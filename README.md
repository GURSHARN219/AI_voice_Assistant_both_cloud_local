# 🎤 Sophia AI Assistant

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](https://github.com/your-username/sophia-ai-assistant)

A sophisticated voice-enabled AI assistant built with Python, featuring real-time speech recognition, natural language processing, and text-to-speech capabilities. Meet Sophia - your intelligent, conversational AI companion with a modern GUI interface.

![Sophia AI Assistant](image1.png)
*Sophia AI Assistant - Main Interface*

![AI Interaction Demo](image2.png)
*Real-time Voice Interaction with Visual Feedback*

## ✨ Features

- 🎙️ **Real-time Speech Recognition** - Advanced voice activity detection with WebRTC VAD
- 🧠 **Intelligent Conversations** - Powered by state-of-the-art language models via OpenRouter
- 🔊 **Natural Text-to-Speech** - High-quality voice synthesis with Kokoro TTS
- 🖥️ **Modern GUI Interface** - Clean, dark-themed interface built with CustomTkinter
- 🔄 **Fallback System** - Automatic switching between cloud and local LLM providers
- 📊 **Visual Indicators** - Real-time status monitoring for STT, LLM, and TTS processes
- 🌙 **Theme Toggle** - Light/dark mode support
- 🔇 **TTS Control** - Easy toggle for text-to-speech functionality

## 🛠️ Core Technologies & Libraries

### **CustomTkinter**

Modern and customizable Python UI-library based on Tkinter.
Provides beautiful, native-looking GUI components with dark/light theme support.
Used for creating the main application interface, buttons, and visual indicators.
Enables smooth threading integration for real-time audio processing without UI freezing.

### **Faster-Whisper**

High-performance implementation of OpenAI's Whisper model for automatic speech recognition.
Optimized for speed and memory efficiency using CTranslate2 backend.
Supports GPU acceleration with CUDA for real-time transcription capabilities.
Provides accurate multilingual speech-to-text conversion with beam search optimization.

### **Kokoro TTS**

Advanced neural text-to-speech synthesis model for natural voice generation.
Delivers high-quality, human-like speech output with emotional expressiveness.
Supports multiple voice styles and languages for diverse conversational experiences.
Optimized for real-time streaming audio generation with low latency.

### **OpenAI Python Client**

Official OpenAI API client for seamless integration with language models.
Supports both OpenRouter cloud services and local LM Studio instances.
Handles authentication, rate limiting, and error management automatically.
Enables flexible model switching and fallback mechanisms for reliability.

### **PyTorch**

Deep learning framework powering the AI models for speech and language processing.
Provides GPU acceleration support for faster inference on compatible hardware.
Handles tensor operations for audio processing and neural network computations.
Enables efficient model loading and memory management for real-time applications.

### **SoundDevice & WebRTC VAD**

Professional audio input/output handling with real-time voice activity detection.
Captures high-quality audio streams with configurable sample rates and formats.
Implements intelligent silence detection to optimize speech recognition accuracy.
Provides cross-platform audio device compatibility and low-latency processing.

### **NumPy**

Fundamental package for scientific computing and numerical operations.
Handles audio signal processing, waveform manipulation, and mathematical computations.
Provides efficient array operations for real-time audio data transformation.
Enables seamless integration between audio libraries and AI model inputs.

### **AsyncIO & Threading**

Asynchronous programming support for non-blocking audio processing and API calls.
Ensures responsive GUI while handling intensive AI computations in background.
Manages concurrent operations for simultaneous STT, LLM, and TTS processing.
Provides thread-safe communication between GUI and backend services.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- CUDA-compatible GPU (optional, for faster processing)
- Microphone and speakers/headphones
- Internet connection (for OpenRouter API)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/sophia-ai-assistant.git
   cd sophia-ai-assistant
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Download AI Models**
   
   **Faster-Whisper Model:**
   - Download from: [🤗 Faster-Whisper Large V3 Turbo](https://huggingface.co/deepdml/faster-whisper-large-v3-turbo-ct2)
   - Update the model path in `stt_handler.py`
   
   **Kokoro TTS Model:**
   - Auto-downloads from: [🤗 Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
   - No manual setup required

4. **Configure API Keys**
   
   Copy the example environment file and add your API key:

   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your OpenRouter API key:

   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
   
   Get your API key from: [🔑 OpenRouter API Keys](https://openrouter.ai/settings/keys)

5. **Set up Local LLM (Optional)**
   
   For offline capabilities, install LM Studio:
   - Download: [🖥️ LM Studio](https://lmstudio.ai/)
   - Load model: [🤗 Gemma-3-4B](https://lmstudio.ai/models/google/gemma-3-4b)
   - Start local server on `localhost:1234`

### Running the Application

```bash
python main.py
```

## 🎯 Usage

1. **Launch Sophia** - Run the main application
2. **Voice Input** - Click the microphone button and speak
3. **Text Input** - Type your message in the input field and press Enter
4. **Settings** - Use the theme toggle and TTS controls in the status bar
5. **Monitor Status** - Watch the STT, LLM, and TTS indicators for real-time feedback

## 🔧 Configuration

### Model Paths

Update the model paths in the respective handler files:

- `codes/stt_handler.py` - Whisper model location
- `codes/llm_handler.py` - LLM provider settings
- `codes/tts_handler.py` - Kokoro model configuration

### API Settings

Configure your preferred LLM providers in `codes/llm_handler.py`:

- Primary: OpenRouter (cloud-based)
- Fallback: LM Studio (local)

## 📂 Project Structure

```text
sophia-ai-assistant/
├── main.py                  # Application entry point
├── codes/
│   ├── gui.py               # Main GUI interface
│   ├── llm_handler.py       # Language model integration
│   ├── stt_handler.py       # Speech-to-text processing
│   ├── tts_handler.py       # Text-to-speech synthesis
│   ├── simulation.py        # Visual effects and animations
│   └── test.py             # Testing and development utilities
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for Whisper speech recognition
- [OpenRouter](https://openrouter.ai/) for LLM API access
- [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) for high-quality TTS
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for modern GUI components

## 📞 Support

If you encounter any issues or have questions, please [open an issue](https://github.com/your-username/sophia-ai-assistant/issues) on GitHub.

---

**Made with ❤️ and AI** | *Sophia AI Assistant - Your Intelligent Conversation Partner*
