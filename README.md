# App Watch

A self-hosted tool to monitor iOS App Store apps for new releases and automatically notify you via multiple platforms (Discord, Slack, Telegram, Microsoft Teams, Email, or custom webhooks). Features a web interface for easy management of multiple apps.

## Features

- 🍎 Monitor multiple iOS App Store apps simultaneously
- 🔔 Automatic notifications when new versions are detected (Discord, Slack, Telegram, Teams, Email, or custom webhooks)
- 📝 Formats release notes for better readability across platforms
- 🖥️ Web-based interface for configuration and management
- 🔄 Configurable check intervals per app
- ⚡ Manual check and post buttons for testing
- 🚫 Duplicate prevention - tracks last posted version
- 🔧 Generic settings for reusable webhook configurations (Telegram bot token, SMTP settings)

## Getting Started

### Step 1: Set Up Docker

If you don't have Docker installed, download it from [docker.com](https://www.docker.com/get-started).

### Step 2: Create the Configuration File

Create a file named `docker-compose.yml` in a folder on your computer. Copy and paste this content:

```yaml
services:
  app-watch:
    image: rajnishdock/app-watch:latest
    container_name: app-watch
    restart: unless-stopped
    ports:
      - "8192:8192"
    volumes:
      - ./data:/data
```

**Note:** The `./data` folder will be created automatically to store your app settings and version tracking data.

### Step 3: Start the Application

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) in the folder where you created `docker-compose.yml` and run:

```bash
docker compose up -d
```

Wait a few seconds for it to start, then open your web browser and go to:

**http://localhost:8192**

### Step 4: Set Up Notification Destination

Before adding apps, you need to configure at least one notification destination. The application supports multiple platforms:

**Discord:**
1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook** or **Create Webhook**
4. Choose the channel where you want notifications
5. Name it (e.g., "App Releases")
6. Click **Copy Webhook URL** and save it

**Slack:**
1. Go to your Slack workspace settings
2. Navigate to **Apps** → **Incoming Webhooks**
3. Click **Add to Slack** or **Create Webhook**
4. Choose the channel and click **Add Incoming Webhooks Integration**
5. Copy the webhook URL (starts with `https://hooks.slack.com/`)

**Telegram:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions to create a bot
3. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Message [@userinfobot](https://t.me/userinfobot) to get your chat ID
5. You can set the bot token in Settings for all apps, or per app

**Microsoft Teams:**
1. Go to your Teams channel
2. Click **⋯** (More options) → **Connectors**
3. Search for "Incoming Webhook" and click **Configure**
4. Name it and click **Create**
5. Copy the webhook URL

**Email (SMTP):**
- Configure SMTP settings in Settings page (host, port, username, password)
- Or configure per app when adding notification destination
- Common providers: Gmail (smtp.gmail.com:587), Outlook (smtp-mail.outlook.com:587)

**Generic Webhook:**
- Any HTTP/HTTPS endpoint that accepts POST requests
- Optionally customize the JSON payload template

### Step 5: Find App Store ID

1. Go to [apps.apple.com](https://apps.apple.com) in your browser
2. Search for the app you want to monitor
3. Open the app's page
4. Look at the URL - it will look like: `https://apps.apple.com/app/id123456789`
5. Copy the number after `/id` (that's your App Store ID)

### Step 6: Add Your First App

1. In the web interface (http://localhost:8192), click **"Add App"**
2. Fill in:
   - **App Name**: Any name you want (e.g., "My App")
   - **App Store ID**: The number you found in Step 5
   - **Notification Destination**: Select your preferred platform (Discord, Slack, Telegram, Teams, Email, or Generic)
   - **Configure the destination**: Enter the required information based on your selected platform:
     - **Discord/Slack/Teams/Generic**: Paste the webhook URL
     - **Telegram**: Enter bot token (or use from Settings) and chat ID
     - **Email**: Enter recipient email and SMTP settings (or use from Settings)
   - **Check Interval** (optional): Leave empty for default (12 hours), or use `6h`, `1d`, etc.
3. Click **"Save"**

**Note:** You can add multiple notification destinations per app. Just add another destination in the same form.

### Step 7: Test It

1. Click **"Check Now"** to see if it finds the current version
2. Click **"Post Now"** to send a test message to all configured notification destinations
3. If everything works, the app will check for updates automatically

You can add more apps by clicking **"Add App"** again. Each app can use different notification destinations and channels.

## Security and network exposure

**Web interface:** App Watch does **not** provide login, passwords, or other built-in access control for the UI. Anyone who can open the server URL in a browser can use the application (manage apps, change settings, send notifications, and so on).

**If you expose the app beyond your own machine** (LAN, VPS, port forwarding, cloud host, etc.), you are responsible for restricting who can reach it. Common approaches:

- **Reverse proxy with TLS**: Place [Caddy](https://caddyserver.com/), [nginx](https://nginx.org/), [Traefik](https://traefik.io/), or another reverse proxy in front of the container, terminate HTTPS at the proxy, and apply any access rules or authentication the proxy supports.
- **Private network access**: Use [Tailscale](https://tailscale.com/), [WireGuard](https://www.wireguard.com/), another VPN, or SSH port forwarding so the UI is only reachable from trusted devices, not from the public internet.
- **Firewall and binding**: Restrict inbound traffic with host or cloud firewall rules so only trusted networks or IPs can reach the app port. You can also bind the published port to localhost only (for example `127.0.0.1:8192:8192` in Docker Compose) and access the UI via SSH tunnel or VPN.

**API key (Settings → Security):** The UI shows an API key for scripts and integrations (for example `X-Api-Key` or `Authorization: Bearer`). **The application does not currently require this key to call the REST API**—if someone can reach your instance over the network, they can use the API without it—so **network-level protection** (above) is what actually restricts access. You should still **treat the API key as a secret**: do not commit it to repositories, paste it into public issues, or share it unnecessarily, and use **Regenerate** if it may have leaked, so automation and any future hardening remain trustworthy.

## How It Works

The application periodically checks the App Store API for new versions of your configured apps. When a new version is detected, it automatically formats the release notes and sends notifications to all configured destinations (Discord, Slack, Telegram, Teams, Email, or custom webhooks).

- **Default check interval**: Every 12 hours (configurable per app)
- **Custom intervals**: Set different check frequencies per app (e.g., `6h` for 6 hours, `1d` for daily)
- **Manual checks**: Use the "Check Now" button to trigger an immediate check
- **Multiple destinations**: Configure multiple notification channels per app (e.g., Discord + Email)
- **Duplicate prevention**: Tracks the last posted version to avoid sending the same update multiple times
- **Version tracking**: Stores version history locally in the data directory
- **Generic settings**: Set reusable configurations (Telegram bot token, SMTP settings) in Settings page

## Release Notes Formatting

The application automatically formats release notes from the App Store for better readability across all platforms. It detects structured sections and formats them appropriately for each notification type (Discord, Slack, Telegram, Teams, Email, etc.).

### Example: Structured Release Notes

**Original App Store release notes:**
```
New:
- Dark mode support
- New dashboard design

Improvements:
- Faster app startup
- Better error handling

Fixed:
- Crash on login
- Memory leak issue
```

**Formatted output (Discord/other platforms):**
```
# v2.3.1

## New
- Dark mode support
- New dashboard design

## Improvements
- Faster app startup
- Better error handling

## Fixed
- Crash on login
- Memory leak issue
```

### Section Headers That Become Bold

The formatter automatically detects and formats these section headers appropriately for each platform:

- **New** (or "new:")
- **Added** (or "added:")
- **Improvements** (or "improvements:", "improved:")
- **Fixed** (or "fixed:", "fixes:", "bugs:", "bug:")
- **Changes** (or "changes:", "change:")

If your release notes don't have these section headers, they'll be formatted as a simple bullet list with the version number.

### Example: Generic Release Notes

**Original App Store release notes:**
```
This release includes bug fixes and performance improvements.
We've also added support for iOS 17.
```

**Formatted output (Discord/other platforms):**
```
# v2.3.1

- This release includes bug fixes and performance improvements.
- We've also added support for iOS 17.
```

### Customizing Formatting

The formatting behavior can be customized by modifying the formatter configuration in the source code. The formatter recognizes common section headers and can be extended to support additional patterns if needed.

## Managing the Application

### Starting and Stopping

**Start the application:**
```bash
docker compose up -d
```

**Stop the application:**
```bash
docker compose down
```

**Restart the application:**
```bash
docker compose restart
```

**View logs:**
```bash
docker logs app-watch
```

**View logs in real-time:**
```bash
docker logs -f app-watch
```

### Alternative Deployment Methods

**Using Docker Run (without Docker Compose):**

```bash
docker run -d \
  --name app-watch \
  --restart unless-stopped \
  -p 8192:8192 \
  -v $(pwd)/data:/data \
  rajnishdock/app-watch:latest
```

**Building from Source:**

If you want to build from source or make modifications:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/app-watch.git
cd app-watch

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Build and run with Docker Compose
docker compose build
docker compose up -d
```

## Configuration

### Data Storage

All your app configurations and version tracking data are stored in the `data` folder in the same directory as your `docker-compose.yml` file:

- `data/apps.json` - App configurations (names, IDs, notification destinations, intervals)
- `data/settings.json` - Global settings (default interval, Telegram bot token, SMTP settings)
- `data/apps/<APP_ID>/version.txt` - Last posted version for each app
- `data/apps/<APP_ID>/check.txt` - Last check timestamp for each app

**Important:** If you delete the `data` folder, you'll lose all your app configurations and version tracking.

### Docker Compose Configuration

The `docker-compose.yml` file supports many configuration options. Here's a comprehensive example with all possible values:

```yaml
services:
  app-watch:
    # Image configuration
    image: rajnishdock/app-watch:latest        # Docker image to use
    container_name: app-watch                  # Custom container name (optional)
    
    # Restart policy
    restart: unless-stopped                    # Options: no, always, on-failure, unless-stopped
    
    # Port mapping (host:container)
    ports:
      - "8192:8192"                            # Format: "HOST_PORT:CONTAINER_PORT"
      # Alternative formats:
      # - "8192:8192/tcp"                      # Specify protocol
      # - "127.0.0.1:8192:8192"               # Bind to specific host IP
    
    # Volume mounts
    volumes:
      - ./data:/data                           # Local path:container path
      # Alternative formats:
      # - /docker-data/app-watch/data:/data    # Absolute path
      # - app-watch-data:/data                 # Named volume (requires volumes: section)
    
    # Environment variables
    environment:
      - CHECK_INTERVAL=12h                     # Default check interval (12h, 6h, 1d, 30m, etc.)
      - PORT=8192                              # Server port (default: 8192)
      - TZ=America/New_York                    # Timezone (optional, e.g., UTC, Europe/London)
      - APP_VERSION=1.0.0                      # App version override (optional)
    # Alternative: use env_file
    # env_file:
    #   - .env                                  # Load from .env file
    #   - .env.local                            # Multiple files supported
    
    # Networks (optional)
    networks:
      - app-watch-network                      # Custom network name
    # Or use default network
    
    # Health check (optional) — uses lightweight /health (see Dockerfile HEALTHCHECK)
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8192/health"]
      interval: 30s                            # Check every 30 seconds
      timeout: 5s                              # Fail if the probe runs longer than this
      retries: 3                               # Retry 3 times before marking unhealthy
      start_period: 40s                        # Grace period on startup
    
    # Resource limits (optional)
    deploy:
      resources:
        limits:
          cpus: '1.0'                          # CPU limit (1.0 = 1 CPU core)
          memory: 512M                         # Memory limit
        reservations:
          cpus: '0.5'                          # CPU reservation
          memory: 256M                         # Memory reservation
    
    # Logging configuration (optional)
    logging:
      driver: "json-file"                      # Options: json-file, syslog, journald, gelf, fluentd, awslogs, splunk, etwlogs, none
      options:
        max-size: "10m"                        # Max log file size
        max-file: "3"                          # Number of log files to keep
    
    # Labels (optional)
    labels:
      - "com.example.description=App Watch"
      - "com.example.version=1.0"
    
    # User and permissions (optional)
    # user: "1000:1000"                        # Run as specific user:group (UID:GID)
    
    # Working directory (optional)
    # working_dir: /app                        # Override working directory
    
    # Command override (optional)
    # command: ["python", "-m", "backend.app", "--custom-arg"]
    
    # Entrypoint override (optional)
    # entrypoint: ["/custom-entrypoint.sh"]
    
    # Security options (optional)
    # security_opt:
    #   - no-new-privileges:true
    
    # Capabilities (optional)
    # cap_add:
    #   - NET_ADMIN
    # cap_drop:
    #   - ALL
    
    # Shared memory size (optional)
    # shm_size: '64mb'
    
    # Dependencies (optional)
    # depends_on:
    #   - database
    #   - redis

# Named volumes (if using named volumes)
# volumes:
#   app-watch-data:
#     driver: local
#     # Optional volume options:
#     # driver_opts:
#     #   type: none
#     #   o: bind
#     #   device: /path/to/data

# Networks (if using custom networks)
# networks:
#   app-watch-network:
#     driver: bridge
#     # Optional network options:
#     # ipam:
#     #   config:
#     #     - subnet: 172.20.0.0/16
```

#### Environment Variables Reference

| Variable | Description | Default | Format/Examples |
|----------|-------------|---------|-----------------|
| `CHECK_INTERVAL` | Default check interval for apps without custom intervals | `12h` | `30m`, `6h`, `12h`, `1d`, `7d` |
| `PORT` | Server port number | `8192` | Any valid port number (e.g., `3000`, `8080`) |
| `TZ` | Timezone for timestamps and logging | System timezone | `UTC`, `America/New_York`, `Europe/London`, `Asia/Tokyo` |
| `APP_VERSION` or `VERSION` | Application version override | Auto-detected | Version string (e.g., `1.0.0`) |

#### Restart Policy Options

- `no`: Do not automatically restart the container (default)
- `always`: Always restart the container if it stops
- `on-failure`: Restart the container if it exits due to an error
- `unless-stopped`: Always restart the container unless it is explicitly stopped

#### Volume Mount Options

- **Bind mount**: `./data:/data` or `/absolute/path:/data` - Maps a host directory to container directory
- **Named volume**: `app-watch-data:/data` - Uses Docker-managed volume (requires `volumes:` section)
- **Read-only mount**: `./data:/data:ro` - Mount as read-only

#### Port Mapping Formats

- `"8192:8192"` - Map host port 8192 to container port 8192
- `"127.0.0.1:8192:8192"` - Bind to specific host IP only
- `"8192:8192/tcp"` - Specify protocol (tcp/udp)
- `"8192:8192/udp"` - UDP protocol

#### Health Check Options

The image defines a **`HEALTHCHECK`** that probes **`GET /health`** on `127.0.0.1` using the container’s **`PORT`** (default `8192`). That endpoint returns only `{"status":"ok"}` and does not run the scheduler or touch disk, so it is safe for frequent liveness probes.

Use **`GET /api/status`** when you want richer JSON (version, scheduler thread, job count); it may restart the scheduler if the worker thread died, so it is better for monitoring than for high-frequency Docker health checks.

If you override **`PORT`**, override the health check URL in Compose/Kubernetes to use the same port.

**Kubernetes example (liveness):**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8192
  initialDelaySeconds: 40
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

You can customize Compose `healthcheck` fields as needed:

- `interval`: Time between health checks
- `timeout`: Maximum time to wait for a response
- `retries`: Number of consecutive failures before marking unhealthy
- `start_period`: Grace period on startup before health checks count

#### Resource Limits

Use the `deploy.resources` section to limit container resources:
- `limits`: Maximum resources the container can use
- `reservations`: Guaranteed minimum resources

**Note:** The `deploy` section is primarily for Docker Swarm, but some options work with `docker compose`. For standalone Docker Compose, you can also use deprecated but still functional options:
```yaml
mem_limit: 512m
cpus: 1.0
```

#### Logging Drivers

Common logging driver options:
- `json-file`: Default, logs to JSON files (supports `max-size` and `max-file` options)
- `syslog`: Send logs to syslog
- `journald`: Send logs to systemd journal (Linux only)
- `none`: Disable logging

### Per-App Settings

Each app can be configured individually through the web interface:

- **App Name**: Display name for easy identification
- **App Store ID**: Unique identifier from the App Store URL
- **Notification Destinations**: One or more notification channels (Discord, Slack, Telegram, Teams, Email, or Generic webhook)
  - Each destination can be configured with its specific settings
  - You can add multiple destinations of the same or different types
- **Check Interval**: Override the default interval (e.g., `6h`, `30m`, `1d`)
- **Enabled**: Toggle to enable/disable monitoring for specific apps

### Global Settings

Configure reusable settings in the Settings page:

- **Default Check Interval**: Default interval for all apps (unless overridden)
- **Monitoring Enabled by Default**: Whether new apps start enabled
- **Auto-Post on Update**: Automatically send notifications when updates are detected
- **Telegram Bot Token**: Default bot token for all Telegram notifications (can be overridden per app)
- **SMTP Settings**: Default email server settings (host, port, username, password, from address, TLS)
  - These can be used for all email notifications or overridden per app

## Troubleshooting

### Container Won't Start

**Port already in use:**
- Check if port 8192 is already in use by another application
- On Linux/Mac: `lsof -i :8192` or `netstat -an | grep 8192`
- On Windows: `netstat -ano | findstr :8192`
- Change the port in `docker-compose.yml` if needed

**Permission issues:**
- Ensure Docker has permission to access the data directory
- On Linux/Mac: `chmod 755 ./data` (if the folder exists)
- The `./data` folder will be created automatically with proper permissions

**Docker not running:**
- Verify Docker Desktop (or Docker daemon) is running
- Check Docker status: `docker ps`

### Notifications Not Working

**Discord/Slack/Teams/Generic Webhook issues:**
- Verify the webhook URL is correct:
  - Discord: Must start with `https://discord.com/api/webhooks/`
  - Slack: Must start with `https://hooks.slack.com/`
  - Teams: Must be a valid HTTPS URL
  - Generic: Must start with `http://` or `https://`
- Ensure you copied the entire URL without any extra spaces or characters
- Test the webhook manually using curl:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
    -d '{"content":"Test message"}' \
    YOUR_WEBHOOK_URL
  ```

**Webhook deleted or invalid:**
- If you deleted the webhook, create a new one and update the app configuration
- Check that the webhook has permission to post in the selected channel
- Verify the webhook is still active in the platform's settings

**Telegram issues:**
- Verify the bot token is correct (format: `123456789:ABCdef...`)
- Check that the chat ID is correct (get it from @userinfobot)
- Ensure the bot token is set either in Settings or per app
- Make sure you've started a conversation with your bot first

**Email (SMTP) issues:**
- Verify SMTP settings are correct (host, port, username, password)
- For Gmail, use an App Password instead of your regular password
- Check that SMTP settings are set either in Settings or per app
- Verify the recipient email address is correct
- Test SMTP connection manually if needed

**No notifications received:**
- Use the "Post Now" button to test manually
- Check the container logs for errors: `docker logs app-watch`
- Verify the app is enabled in the web interface
- Check that at least one notification destination is properly configured

### App Not Detecting Updates

**App Store ID incorrect:**
- Double-check the App Store ID contains only numbers
- Verify the ID by visiting: `https://apps.apple.com/app/id<YOUR_ID>`
- The ID should be in the URL format: `apps.apple.com/app/id123456789`

**Check interval too long:**
- Reduce the check interval to test more frequently (e.g., `30m` for testing)
- Use the "Check Now" button to trigger an immediate check
- Check the "Last Check" timestamp in the web interface

**App Store API issues:**
- The App Store API may be slow or temporarily unavailable
- Wait a few minutes and try the "Check Now" button again
- Check container logs for API errors: `docker logs app-watch`

### Common Errors

**"Invalid Discord webhook URL"**
- The URL must start with `https://discord.com/api/webhooks/`
- Ensure there are no spaces or extra characters
- If using an old webhook URL with `discordapp.com`, update it to `discord.com`

**"Invalid Slack webhook URL"**
- The URL must start with `https://hooks.slack.com/`
- Ensure you copied the complete webhook URL from Slack

**"Telegram bot token is required"**
- Set the bot token in Settings page, or provide it when configuring the app
- Get the token from @BotFather on Telegram

**"Telegram chat ID is required"**
- Get your chat ID from @userinfobot on Telegram
- Or extract it from Telegram message updates

**"SMTP host is required"**
- Set SMTP host in Settings page, or provide it when configuring email destination
- Common values: `smtp.gmail.com`, `smtp-mail.outlook.com`

**"Invalid webhook URL"**
- For generic webhooks, ensure the URL starts with `http://` or `https://`
- Verify the endpoint accepts POST requests with JSON payload

**"App Store ID must be a number"**
- Only use the numeric ID from the App Store URL
- Example: For `https://apps.apple.com/app/id123456789`, use `123456789`
- Remove any non-numeric characters

**"Invalid interval format"**
- Use the format: `<number><unit>` where unit is `m` (minutes), `h` (hours), or `d` (days)
- Examples: `30m`, `6h`, `12h`, `1d`, `7d`
- Leave empty to use the default interval (12 hours)

## API Endpoints

The application provides a REST API for programmatic access. Integrations can send the API key from **Settings → Security** as `X-Api-Key: <your-key>` or `Authorization: Bearer <your-key>` where supported. **The server does not enforce authentication on these endpoints today**—whoever can reach the service can call the API—so rely on [network exposure controls](#security-and-network-exposure) for real protection, and still keep the API key private.

- `GET /health` - Lightweight liveness (JSON `{"status":"ok"}`); intended for Docker/Kubernetes probes
- `GET /api/apps` - List all configured apps
- `POST /api/apps` - Create a new app configuration
- `PUT /api/apps/:id` - Update an existing app
- `DELETE /api/apps/:id` - Delete an app configuration
- `POST /api/apps/:id/check` - Manually trigger a check for updates
- `POST /api/apps/:id/post` - Manually post current version to all configured notification destinations
- `GET /api/settings` - Get application settings
- `PUT /api/settings` - Update application settings
- `GET /api/status` - Status JSON (version, scheduler, jobs); may restart the scheduler if the worker thread died

## Technical Details

- **Backend**: Python 3.11 with Flask
- **Frontend**: React 18
- **Scheduling**: Automatic checks using the `schedule` library
- **Storage**: JSON-based file storage for app configurations
- **Container**: Docker with multi-stage builds

## Contributing

Contributions are welcome! If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this for personal or commercial projects.
