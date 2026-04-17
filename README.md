# 🤖 StanlBot: Premium AI Assistant

StanlBot is a high-performance, cloud-native Telegram bot designed for resource-constrained Micro EC2 environments. It blends academic productivity, personal finance tracking, and AI-powered automation into a seamless "Glassy" dashboard experience.

## ✨ Key Features

### 🎓 Academic Productivity
- **AI Assignment Breakdown**: Use `/breakdown` to split complex assignments into actionable study steps.
- **Smart Prioritization**: Use `/prioritize` to let Gemini analyze your deadlines and suggest a focus plan.
- **Deadline Reminders**: Automated scheduling for upcoming CATs and assignments.

### 💰 Financial Intelligence
- **📲 AI Transaction Parsing**: Paste your **M-Pesa, Airtel Money, or Bank SMS** directly. The bot automatically extracts amounts, categories, and descriptions.
- **📊 Visual Analytics**: Generate stunning spending charts with `/summary_chart` using Pillow.
- **🧠 Budget Review**: Get professional financial tips from AI based on your actual spending habits.
- **🚨 Smart Alerts**: Receive real-time warnings when you approach or exceed your category budgets.

### 🧠 Knowledge & AI
- **Hybrid Search**: Unified `/find` command that combines SQLite FTS5 (exact matches) with ChromaDB RAG (semantic meaning).
- **Infinite Trivia**: AI-generated quiz questions powered by Gemini.
- **Glassy Dashboard**: A premium, callback-driven UI for smooth mobile navigation.

## 🛠 Tech Stack
- **Core**: Aiogram 3.x (Python)
- **AI**: Google Gemini (Flash 2.5) for LLM and Embeddings.
- **Database**: 
  - SQLite (Local persistence)
  - FTS5 (High-speed indexed search)
  - ChromaDB (Vector store for RAG)
- **Monitoring**: Psutil-based server health tracking.

## 🚀 Deployment
Designed for **Ubuntu on AWS Micro EC2**.
1. Clone the repo.
2. Setup virtual environment: `python -m venv .venv`
3. Install requirements: `pip install -r requirements.txt`
4. Configure `.env` (API Keys, Admin IDs).
5. Run: `python main.py`

## 🔒 Security & RBAC
- **Admin-Only DevOps**: Tools like `/ec2`, `/deploy`, and server stats are strictly limited to IDs defined in the configuration.
- **Encrypted Local Storage**: SQLite DB with WAL mode for data integrity.

---
*Built with ❤️ for StanlleyEdu Evolution.*
