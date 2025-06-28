const demoapp = {
    text: '讲个冷笑话吧，要很好笑的那种。',
    recording: false,
    asrWS: null,
    currentText: null,
    disabled: false,
    elapsedTime: null,
    logs: [{ idx: 0, text: 'Happily here at ruzhila.cn.' }],
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
        
        if (this.currentText) {
            this.logs.push({ idx: this.logs.length + 1, text: this.currentText });
        }
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

        ws.onopen = () => {
            this.logs = [];
        };

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            const { text, start_time, finished, idx } = data;

            currentMessage = text;
            this.currentText = text

            if (finished) {
                this.logs.push({ text: currentMessage, startTime:start_time, idx: idx });
                currentMessage = '';
                this.currentText = null
            }
        };

        // 创建音频上下文并保存引用
        this.currentAudioContext = new AudioContext({ sampleRate: 16000 });
        await this.currentAudioContext.audioWorklet.addModule('./audio_process.js');

        const recordNode = new AudioWorkletNode(this.currentAudioContext, 'record-audio-processor');
        recordNode.connect(this.currentAudioContext.destination);
        recordNode.port.onmessage = (event) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const int16Array = event.data.data;
                ws.send(int16Array.buffer);
            }
        }
        
        // 创建媒体源并保存引用
        this.currentMediaSource = this.currentAudioContext.createMediaStreamSource(mediaStream);
        this.currentMediaSource.connect(recordNode);
        
        this.asrWS = ws;
        this.recording = true;
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
}

window.demoapp = demoapp;