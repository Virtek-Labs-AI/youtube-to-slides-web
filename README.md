# YouTube to Slides

A web application that generates PowerPoint presentations from YouTube videos using AI. Paste a YouTube URL, and the app extracts the transcript, uses Claude AI to create structured slides with timestamped references, and renders a downloadable `.pptx` file. Optionally import directly into Google Slides.

## Architecture

```
                         +-------------------+
                         |   Next.js 14 UI   |
                         |   (port 3000)     |
                         +--------+----------+
                                  |
                                  | REST API
                                  v
                         +--------+----------+
                         |  FastAPI Backend   |
                         |   (port 8000)     |
                         +--+-----+-------+--+
                            |     |       |
               +------------+     |       +------------+
               |                  |                    |
               v                  v                    v
      +--------+---+    +--------+--------+   +-------+--------+
      | PostgreSQL |    | Redis (broker)  |   | Celery Worker  |
      | (port 5432)|    | (port 6379)     |   | (background)   |
      +------------+    +-----------------+   +-------+--------+
                                                      |
                                              +-------+--------+
                                              | - YouTube API  |
                                              | - Claude AI    |
                                              | - Google APIs  |
                                              +----------------+
```

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Frontend       | Next.js 14, React, Tailwind CSS     |
| Backend        | FastAPI, Python 3.12                |
| Task Queue     | Celery + Redis                      |
| Database       | PostgreSQL 16                       |
| AI             | Anthropic Claude (via API)          |
| Slide Rendering| python-pptx                         |
| Auth           | Google OAuth 2.0                    |
| Google Import  | Google Drive & Slides APIs          |
| Containerization| Docker Compose                     |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A [Google Cloud Console](https://console.cloud.google.com/) project
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ryanbyrne30/youtube-to-slides-web.git
cd youtube-to-slides-web
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values (see sections below).

### 3. Google Cloud Console setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or select an existing one).
2. Navigate to **APIs & Services > Library** and enable:
   - **Google Drive API**
   - **Google Slides API**
3. Navigate to **APIs & Services > Credentials** and click **Create Credentials > OAuth 2.0 Client ID**.
4. Set the application type to **Web application**.
5. Add `http://localhost:8000/api/auth/callback/google` as an **Authorized redirect URI**.
6. Copy the **Client ID** and **Client Secret** into your `.env` file:
   ```
   GOOGLE_CLIENT_ID=<your-client-id>
   GOOGLE_CLIENT_SECRET=<your-client-secret>
   ```

### 4. Anthropic API key

1. Sign up or log in at [console.anthropic.com](https://console.anthropic.com/).
2. Navigate to **API Keys** and create a new key.
3. Paste it into your `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

### 5. Start the application

```bash
docker compose up --build
```

The frontend will be available at **http://localhost:3000** and the API at **http://localhost:8000**.

## Usage

1. Open **http://localhost:3000** in your browser.
2. Sign in with your Google account.
3. Paste a YouTube video URL into the input field and click **Generate**.
4. The app will extract the transcript, generate slides using Claude AI, and render a PowerPoint file.
5. Once complete, download the `.pptx` file or import it directly into Google Slides.

Each slide includes timestamped hyperlinks back to the relevant moments in the original video.

## Development

To run services individually for development:

```bash
# Start only infrastructure
docker compose up db redis

# Run backend locally
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Run frontend locally
cd frontend
npm install
npm run dev
```

## License

MIT
