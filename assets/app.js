const demoapp = {
    text: '讲个冷笑话吧，要很好笑的那种。',
    recording: false,
    asrWS: null,
    currentText: null,
    disabled: false,
    elapsedTime: null,
    logs: [],
    // 添加系统状态管理
    systemStatus: {
        apiConnection: 'Checking...',
        apiConnectionActive: false,
        lastChecked: null
    },
    // 添加音频上下文管理
    currentAudioContext: null,
    currentMediaSource: null,

    
    async init() {
        // 初始化时检查系统状态
        await this.checkSystemStatus();
        // 设置定时检查（每30秒检查一次）
        setInterval(() => {
            this.checkSystemStatus();
        }, 30000);
        this.clearLogs()
        this.logs = [];
        this.scrollToBottom();
    },

    // 检查系统状态
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            this.systemStatus.apiConnection = data.api_connection;
            this.systemStatus.apiConnectionActive = data.api_connection_status;
            this.systemStatus.lastChecked = new Date().toLocaleTimeString();
            
            // console.log('系统状态更新:', this.systemStatus);
        } catch (error) {
            console.error('检查系统状态失败:', error);
            this.systemStatus.apiConnection = 'Error';
            this.systemStatus.apiConnectionActive = false;
            this.systemStatus.lastChecked = new Date().toLocaleTimeString();
        }
    },

    async dotts() {
        let audioContext = new AudioContext({ sampleRate: 16000 })
        await audioContext.audioWorklet.addModule('./audio_process.js')
        const ws = new WebSocket('/tts');
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket 未正确初始化或未连接');
            return;
        }
        ws.onopen = () => {
            ws.send(this.text);
        };
        const playNode = new AudioWorkletNode(audioContext, 'play-audio-processor');
        playNode.connect(audioContext.destination);

        this.disabled = true;
        ws.onmessage = async (e) => {
            if (e.data instanceof Blob) {
                e.data.arrayBuffer().then((arrayBuffer) => {
                    const int16Array = new Int16Array(arrayBuffer);
                    let float32Array = new Float32Array(int16Array.length);
                    for (let i = 0; i < int16Array.length; i++) {
                        float32Array[i] = int16Array[i] / 32768.;
                    }
                    playNode.port.postMessage({ message: 'audioData', audioData: float32Array });
                });
            } else {
                const parsedData = JSON.parse(e.data);
                this.elapsedTime = parsedData && parsedData.elapsed;
                this.disabled = false;
            }
        }
    },

    async stopasr() {
        if (!this.asrWS) {
            return;
        }
        this.asrWS.close();
        this.asrWS = null;
        this.recording = false;
        
        // 清理音频上下文
        if (this.currentAudioContext) {
            await this.currentAudioContext.close();
            this.currentAudioContext = null;
        }
        this.currentMediaSource = null;
        this.currentText = null;
    },

    async doasr() {
        const audioConstraints = {
            video: false,
            audio: true,
        };
        console.log('请求麦克风权限');
        
        const mediaStream = await navigator.mediaDevices.getUserMedia(audioConstraints).catch(err => {
            alert("无法访问麦克风：" + err.message);
            console.error(err);
            return null;
        });
        
        if (!mediaStream) return;
        
        const ws = new WebSocket('/asr');
        let currentMessage = '';
        
        // 保存 this 的引用，避免在回调函数中丢失上下文
        const self = this;

        ws.onopen = () => {
            // self.logs = [];
        };

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            const { text, start_time, finished, idx } = data;

            currentMessage = text;
            self.currentText = text

            if (finished) {
                self.logs.push({ result: currentMessage, time:start_time, idx: self.logs.length });
                // 保存更新后的logs
                self.saveLogs(self.logs);
                currentMessage = '';
                self.currentText = null
            }
        };

        // 创建音频上下文并保存引用
        self.currentAudioContext = new AudioContext({ sampleRate: 16000 });
        await self.currentAudioContext.audioWorklet.addModule('./audio_process.js');

        const recordNode = new AudioWorkletNode(self.currentAudioContext, 'record-audio-processor');
        recordNode.connect(self.currentAudioContext.destination);
        recordNode.port.onmessage = (event) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const int16Array = event.data.data;
                ws.send(int16Array.buffer);
            }
        }
        
        // 创建媒体源并保存引用
        self.currentMediaSource = self.currentAudioContext.createMediaStreamSource(mediaStream);
        self.currentMediaSource.connect(recordNode);
        
        self.asrWS = ws;
        self.recording = true;
    },

    // 简化的AI处理方法
    async processWithAI() {
        this.aiProcessing = true;
        this.aiProcessingResult = null;
        
        try {
            console.log('开始AI处理最新Excel文件...');
            
            const response = await fetch('/ai-process-excel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            this.aiProcessingResult = result;
            
            console.log('AI处理完成:', result);
            
            // 显示处理结果
            const message = `AI处理完成！`;
                
            alert(message);
            
        } catch (error) {
            console.error('AI处理失败:', error);
            alert(`AI处理失败: ${error.message}`);
        } finally {
            this.aiProcessing = false;
        }
    },

    // 保存logs到本地存储
    saveLogs(logs) {
        try {
            // 保存到localStorage
            localStorage.setItem('voiceapi_logs', JSON.stringify(logs));
            console.log('Logs saved successfully:', logs);
            this.scrollToBottom();
            
            // 发送到服务器保存
            // this.saveLogsToServer(logs);
            
        } catch (error) {
            console.error('保存logs失败:', error);
        }
    },

    // 从本地存储加载logs
    // loadLogs() {
    //     try {
    //         const savedLogs = localStorage.getItem('voiceapi_logs');
    //         if (savedLogs) {
    //             const logs = JSON.parse(savedLogs);
    //             console.log('Logs loaded successfully:', JSON.stringify(logs));
    //             return logs;
    //         }
    //     } catch (error) {
    //         console.error('加载logs失败:', error);
    //     }
    //     return [];
    // },
    // 清除本地存储中的logs
    clearLogs() {
        try {
            localStorage.removeItem('voiceapi_logs');
            console.log('Logs cleared successfully');
        } catch (error) {
            console.error('清除logs失败:', error);
        }
    },

    // 发送logs到服务器保存
    async saveResultsToServer() {
        const logs = JSON.parse(localStorage.getItem('voiceapi_logs')) || [];
        console.log('保存结果到服务器:', JSON.stringify(logs));
        try {
            const response = await fetch('/api/results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ results: logs })
            });
            
            if (response.ok) {
                console.log('results saved to server successfully');
            } else {
                console.warn('Failed to save results to server:', response.status);
            }
        } catch (error) {
            console.warn('Error saving results to server:', error);
        }
    },
    // 滚动到容器底部
    scrollToBottom() {
        console.log('滚动到容器底部');
        // 使用 setTimeout 来确保 DOM 更新完成
        setTimeout(() => {
            const container = document.getElementById('messages-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 50);
    }
}

window.demoapp = demoapp;