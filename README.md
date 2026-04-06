<h1 align="center"> Job_alert_bot </h1>
<p align="center"> Your Intelligent 24/7 Career Scout—Automated Job Notifications Delivered Directly to Your Telegram </p>

<p align="center">
  <img alt="Build" src="https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge">
  <img alt="Issues" src="https://img.shields.io/badge/Issues-0%20Open-blue?style=for-the-badge">
  <img alt="Contributions" src="https://img.shields.io/badge/Contributions-Welcome-orange?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge">
</p>
<!-- 
  **Note:** These are static placeholder badges. Replace them with your project's actual badges.
  You can generate your own at https://shields.io
-->

---

### 📑 Table of Contents
- [📖 Overview](#-overview)
- [✨ Key Features](#-key-features)
- [🛠️ Tech Stack \& Architecture](#-tech-stack--architecture)
- [📁 Project Structure](#-project-structure)
- [🔐 Environment Variables](#-environment-variables)
- [🚀 Getting Started](#-getting-started)
- [🔧 Usage](#-usage)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)

---

### 📖 Overview

**Job_alert_bot** is a sophisticated, automated recruitment monitoring solution designed to bridge the gap between job seekers and their next career milestone. By leveraging high-frequency polling of global job boards and delivering curated opportunities through Telegram, it transforms the passive act of job searching into an active, real-time intelligence stream.

> The modern job market is fragmented across dozens of platforms, making it nearly impossible for developers and professionals to track every new opening manually. Important opportunities are often missed because they are buried under noise or posted on niche sites. Job_alert_bot solves this by centralizing global job data, applying personalized filters, and alerting users the moment a matching role becomes available.

The solution provides a streamlined user experience where the bot handles the heavy lifting of API interaction, data normalization, and duplicate prevention, allowing users to focus purely on the application process.

**Architecture Overview:** Built with a robust **Python-based asynchronous core**, the system utilizes the `python-telegram-bot` framework for its messaging interface and `httpx` for high-performance, non-blocking requests to external job aggregators.

---

### ✨ Key Features

Job_alert_bot is engineered with a focus on user value and operational efficiency. Each feature is designed to solve a specific pain point in the recruitment lifecycle.

- 🚀 **Multi-Source Aggregation:** Access a global pool of opportunities by pulling data from verified providers like **Adzuna**, **Remotive**, and **Jooble**. You no longer need to check multiple websites; the bot does it for you.
- 🎯 **Granular Filtering:** Take complete control over your feed. Define your career path using specific parameters such as `keyword` (e.g., Python, DevOps), `location` (e.g., London, Remote), and preferred `sources`.
- 🧠 **Smart Duplicate Prevention:** The bot features an intelligent "Sent Job" tracking system. By maintaining a persistent record of previously shared opportunities, it ensures you never receive the same notification twice, keeping your chat clean and relevant.
- 🧹 **Automated Database Maintenance:** With built-in `cleanup_sent_jobs` logic, the system automatically purges old tracking data after a set period. This ensures the bot remains fast and the underlying storage stays lightweight and efficient.
- 📱 **Real-time Interaction:** Update your preferences on the fly using simple Telegram commands. The bot immediately registers changes to your search criteria, ensuring your next alert reflects your latest career interests.
- 🔒 **User Persistence:** Each user's search settings are saved securely, meaning the bot remembers your preferences even after a restart or update.

---

### 🛠️ Tech Stack & Architecture

The architecture of Job_alert_bot is built for reliability and speed. By choosing asynchronous libraries, the bot can handle multiple users and API calls simultaneously without latency.

| Technology | Purpose | Why it was Chosen |
|:--- |:--- |:--- |
| **Python 3.x** | Core Programming Language | High readability, excellent library support for APIs, and rapid development capabilities. |
| **python-telegram-bot** | Messaging Interface | A feature-rich wrapper for the Telegram Bot API that supports the `job-queue` for scheduled alerts. |
| **httpx** | Async HTTP Client | Provides a modern, fully asynchronous interface for making API requests, essential for scaling bot operations. |
| **python-dotenv** | Configuration Management | Ensures sensitive credentials and API keys are stored securely outside the source code. |
| **SQLite (via bot.py)** | Data Persistence | A lightweight, serverless database used to store user preferences and track sent job IDs. |

---

### 📁 Project Structure

The project follows a clean, modular structure typical of professional Python utilities, ensuring ease of maintenance and clear separation of concerns.

```
📂 rishirajdas05-Job_alert_bot-a1237b3/
├── 📄 .env.example              # Template for required API keys and tokens
├── 📄 .gitignore                # Rules for excluding sensitive files from version control
├── 📄 bot.py                    # Main application logic: DB management, API polling, and Telegram handlers
├── 📄 README.md                 # Project documentation and user guide
├── 📄 requirements.txt          # List of Python dependencies and version constraints
└── 📂 .idea/                    # Project-specific IDE configuration
    ├── 📄 job_bot.iml           # IntelliJ/PyCharm module file
    ├── 📄 misc.xml              # General project metadata
    ├── 📄 modules.xml           # Module tracking
    ├── 📄 vcs.xml               # Version control mapping
    └── 📂 inspectionProfiles/   # Code quality and linting profiles
        ├── 📄 Project_Default.xml
        └── 📄 profiles_settings.xml
```

---

### 🔐 Environment Variables

To operate Job_alert_bot, you must configure several environment variables. These allow the bot to communicate with Telegram and the various job search APIs.

| Variable | Description | Source |
|:--- |:--- |:--- |
| `TELEGRAM_BOT_TOKEN` | Unique token to control your bot. | Obtain via [@BotFather](https://t.me/botfather) |
| `ADZUNA_APP_ID` | Application ID for the Adzuna Job API. | Adzuna Developer Portal |
| `ADZUNA_APP_KEY` | Secret Key for the Adzuna Job API. | Adzuna Developer Portal |
| `ADZUNA_COUNTRY` | Target country code for Adzuna searches (e.g., `us`, `gb`, `in`). | Adzuna API Documentation |
| `JOOBLE_API_KEY` | Access key for the Jooble search engine. | Jooble API Portal |

---

### 🚀 Getting Started

#### Prerequisites
- **Python 3.10+** installed on your system.
- A **Telegram account** to create and interact with the bot.
- API credentials for the supported job boards (Adzuna, Jooble).

#### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/rishirajdas05/Job_alert_bot.git
   cd Job_alert_bot
   ```

2. **Set Up Environment:**
   Create a `.env` file based on the provided template:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and fill in your actual API keys and Telegram token.

3. **Install Dependencies:**
   Use the Python package manager to install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize and Run:**
   Start the bot. On the first run, it will automatically call `init_db()` to create the necessary tables for user tracking and job history.
   ```bash
   python bot.py
   ```

---

### 🔧 Usage

Once the bot is running, you can interact with it directly via Telegram. The bot supports flexible command structures to customize your job alerts.

#### Setting Your Search Preferences
Use the `/set` command to define what you are looking for. The bot parses arguments for keywords, location, and specific sources.

**Command Format:**
`/set keyword=<tags> location=<city/country> sources=<provider_list>`

**Examples:**
*   **Targeted Search:**
    `/set keyword=python,java location=Bangalore sources=remotive,adzuna`
*   **Remote Work Focus:**
    `/set keyword=react,frontend location=remote sources=jooble`

#### How it Works Internally:
1.  **User Registration:** When you use `/set`, the `upsert_user()` function saves your preferences to the database.
2.  **API Polling:** The bot periodically calls `main()` which iterates through all users, fetches jobs from `available_sources()`, and filters them using `keyword_match_any()`.
3.  **Notification:** Jobs are formatted using `fmt_job()` (including Markdown escaping via `esc()`) and sent to your Telegram ID.
4.  **Tracking:** The job ID is recorded via `remember_sent()` to ensure no duplicate alerts are sent in the future.

---

### 🤝 Contributing

We welcome contributions to improve Job_alert_bot! Whether you're fixing a bug, adding a new job source, or improving documentation, your help is appreciated.

### How to Contribute

1. **Fork the repository** - Click the 'Fork' button at the top right of this page.
2. **Create a feature branch** 
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes** - Improve code, documentation, or features.
4. **Test thoroughly** - Ensure the bot still connects to APIs and handles database operations.
5. **Commit your changes** - Write clear, descriptive commit messages.
   ```bash
   git commit -m 'Add: New API source integration for LinkedIn'
   ```
6. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request** - Submit your changes for review.

### Development Guidelines
- ✅ Follow PEP 8 style guidelines for Python code.
- 📝 Ensure all new functions are documented (even if the original code lacked docstrings).
- 🧪 If adding a new job source, ensure it handles API rate limits gracefully.
- 🔄 Maintain backward compatibility with the existing SQLite schema.

---

### 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for complete details.

### What this means:
- ✅ **Commercial use:** You can use this project commercially.
- ✅ **Modification:** You can modify the code to suit your specific job search needs.
- ✅ **Distribution:** You can share the software with others.
- ✅ **Private use:** You can run your own private instance of the bot.
- ⚠️ **Liability:** The software is provided "as is", without warranty of any kind.

---

<p align="center">Made with ❤️ by Rishi Raj Das</p>
<p align="center">
  <a href="#">⬆️ Back to Top</a>
</p>
