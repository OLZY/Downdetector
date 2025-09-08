# Downdetector - Service Monitoring System 
Project for monitoring service failures Mikcom
<p>A system for monitoring service statuses through Downdetector with Telegram bot notifications.</p>

## 📋 Project Structure
<p>├── bot_chat.py # Telegram bot for subscription management</p>
<p>├── bot_parser.py # Downdetector parser</p>
<p>├── api.php # API for database operations</p>
<p>├── service_monitor.php # Request handler for the bot</p>
<p>├── update_db.php # Database update handler</p>
<p>├── db_connect.php # Database connection</p>
<p>└── index.html # Web monitoring interface</p>

## 🚀 Installation and Setup

### 1. Requirements
- **MySQL** database
- **Python 3.8+**
- **PHP 7.4+**
- **Web server** (Apache/Nginx)

### 2. Database Setup

Create database and execute SQL queries:

```sql
CREATE TABLE `down_services` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `service_name` varchar(255) NOT NULL,
  `icon_url` varchar(500) DEFAULT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `reg_1` varchar(100) DEFAULT NULL,
  `per_1` varchar(10) DEFAULT NULL,
  `reg_2` varchar(100) DEFAULT NULL,
  `per_2` varchar(10) DEFAULT NULL,
  `reg_3` varchar(100) DEFAULT NULL,
  `per_3` varchar(10) DEFAULT NULL,
  `service_1` varchar(100) DEFAULT NULL,
  `percent_1` varchar(10) DEFAULT NULL,
  `service_2` varchar(100) DEFAULT NULL,
  `percent_2` varchar(10) DEFAULT NULL,
  `service_3` varchar(100) DEFAULT NULL,
  `percent_3` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_service_name` (`service_name`)
);

CREATE TABLE `service_monitor` (
  `id` varchar(50) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `user_service` varchar(100) DEFAULT NULL,
  `user_service_2` varchar(100) DEFAULT NULL,
  `user_service_3` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
);
```

### 3. File Configuration
Replace the following values in all files:

In api.php, db_connect.php, update_db.php:

$mysqli = new mysqli('localhost', 'NameDataBase', 'Password', 'DataBase');

Replace with your database credentials.

In bot_chat.py:

API_URL = "https://ваш-домен.ру/api/service_monitor.php"
TOKEN = "токен телеграм"

Replace with your domain and Telegram bot token.

### 4. Install Python Dependencies

pip install python-telegram-bot requests beautifulsoup4 schedule aiohttp

### 5. File Placement on Server
Place files on your web server:
/var/www/your-domain/
<p>├── api/</p>
<p>│   ├── api.php</p>
<p>│   ├── service_monitor.php</p>
<p>│   ├── update_db.php</p>
<p>│   └── db_connect.php</p>
<p>├── bot/</p>
<p>│   ├── bot_chat.py</p>
<p>│   └── bot_parser.py</p>
<p>└── public_html/</p>
<p>    └── index.html</p>

### 6. Starting the Bots
```bash
cd /var/www/your-domain/bot
python3 bot_chat.py
```

Start Downdetector Parser:
```bash
cd /var/www/your-domain/bot
python3 bot_parser.py
```

### 7. Cron Setup for Automatic Launch
```bash
# Run parser every 5 minutes
*/5 * * * * cd /path/to/bot && python3 bot_parser.py

# Auto-start bot on reboot
@reboot cd /path/to/bot && python3 bot_chat.py
```

## 📊 Functionality
- Service Monitoring: Automatic service status checks every 5 minutes
- Telegram Bot: Subscription management, outage notifications
- Web Interface: Current service status display
- API: RESTful API for integration

### 🔧 Proxy Configuration
In bot_parser.py configure proxies if needed:
```python
self.proxies = [
    "http://your-proxy-1:port",
    "http://your-proxy-2:port",
]
```

### 📝 Logging
Logs are saved in:
- api.log - API requests
- api_errors.log - API errors

<b>Important: Replace all placeholder values with your actual data before launching!</b>
