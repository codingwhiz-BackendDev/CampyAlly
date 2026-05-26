# ParkEase - Camp Management System

A comprehensive Django-based camp management system featuring parking management, emergency response, lost & found tracking, and security monitoring. Built with modern UI/UX principles and fully responsive design.

## 🌟 Features

### Parking Management
- **Zone-based Parking**: Organized parking zones with real-time occupancy tracking
- **Slot Management**: Individual parking slots with status tracking (Available, Occupied, Reserved, Blocked)
- **Check-in/Check-out System**: Session-based parking with automatic timeout (24 hours default)
- **GPS Integration**: Zone locations with latitude/longitude coordinates
- **Manual Override**: Security staff can manually override zone status
- **Real-time Dashboard**: Live view of parking availability and occupancy rates

### Emergency Response System
- **Multi-type Emergency Reporting**: Medical, Fire, Security, Missing Child, Traffic Accident, Crowd Stampede
- **Severity Levels**: Low, Medium, High, Critical with color-coded alerts
- **Status Tracking**: Reported → Dispatched → On Scene → Resolved/False Alarm
- **GPS Location Detection**: Automatic location capture for reports
- **Live Dashboard**: Real-time monitoring with auto-refresh (8 seconds)
- **Timeline Tracking**: Complete history of status changes and responses
- **SOS Button**: Quick emergency access with pulse animation
- **Safety Guidance**: Context-aware safety tips based on emergency type

### Lost & Found System
- **Unified Reporting**: Single system for lost/found persons and items
- **Category Selection**: Lost Person, Found Person, Lost Item, Found Item
- **Image Upload**: Drag & drop and camera capture support
- **GPS Location**: Automatic location capture
- **Search & Filter**: Filter by category, status, and search by title
- **Claim System**: Found items can be claimed and tracked
- **Conditional Fields**: Age/gender for persons, item type for items

### Security Dashboard
- **Zone Monitoring**: Real-time view of all parking zones
- **Status Override**: Security staff can manually change zone status
- **Activity Tracking**: Monitor parking activity and slot changes
- **Summary Cards**: Quick overview of key metrics

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.9 or higher
- **pip**: Python package manager
- **Git**: For cloning the repository

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ParkEase
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Django**
   ```bash
   pip install django==5.0
   ```

4. **Install Pillow** (for image upload support)
   ```bash
   pip install Pillow
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser** (for admin access)
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create username, email, and password.

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## 📁 Project Structure

```
ParkEase/
├── App/                          # Main Django app
│   ├── __init__.py
│   ├── admin.py                  # Admin configuration
│   ├── apps.py                   # App configuration
│   ├── management/               # Custom management commands
│   ├── migrations/               # Database migrations
│   ├── models.py                 # Database models
│   ├── tests.py                  # Unit tests
│   ├── urls.py                   # App URL routing
│   └── views.py                  # View functions
├── ParkEase/                     # Django project settings
│   ├── __init__.py
│   ├── asgi.py                   # ASGI config
│   ├── settings.py               # Project settings
│   ├── urls.py                   # Main URL routing
│   └── wsgi.py                   # WSGI config
├── static/                       # Static files (CSS, JS)
│   ├── css/                      # Stylesheets
│   │   ├── emergency.css
│   │   ├── emergency_dashboard.css
│   │   ├── emergency_report.css
│   │   ├── index.css
│   │   ├── lost_found.css
│   │   ├── parking.css
│   │   ├── security.css
│   │   └── zone_detail.css
│   └── js/                       # JavaScript files
│       ├── emergency.js
│       ├── emergency_report.js
│       ├── index.js
│       ├── lost_found.js
│       ├── parking.js
│       └── zone_detail.js
├── templates/                    # HTML templates
│   ├── emergency.html
│   ├── emergency_dashboard.html
│   ├── index.html
│   ├── lost_found.html
│   ├── parking_dashboard.html
│   ├── security_dashboard.html
│   └── zone_detail.html
├── media/                        # User-uploaded media files
├── db.sqlite3                    # SQLite database (auto-created)
├── manage.py                     # Django management script
└── README.md                     # This file
```

## 🗄️ Database Models

### Parking Management
- **ParkingZone**: Parking zones with capacity, status, and GPS coordinates
- **ParkingSlot**: Individual parking slots with status and session tracking
- **CheckInSession**: Parking session records with tokens and timestamps

### Emergency Response
- **EmergencyReport**: Emergency reports with type, severity, status, and location
- **EmergencyTimeline**: Status change history for each emergency

### Lost & Found
- **LostFoundReport**: Unified lost/found reports for persons and items

## ⚙️ Configuration

### Database
The project uses SQLite by default (configured in `ParkEase/settings.py`). To use PostgreSQL or MySQL:

1. Install the appropriate database adapter:
   ```bash
   pip install psycopg2-binary  # For PostgreSQL
   # or
   pip install mysqlclient      # For MySQL
   ```

2. Update `DATABASES` in `ParkEase/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'your_db_name',
           'USER': 'your_db_user',
           'PASSWORD': 'your_db_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

### Static Files
Static files are served from the `static/` directory. In production, run:
```bash
python manage.py collectstatic
```

### Media Files
User-uploaded images are stored in the `media/` directory. Ensure this directory exists and is writable.

## 🌐 URL Routes

### Main Routes
- `/` - Home page with navigation to all features
- `/parking/` - Parking dashboard
- `/parking/zone/<id>/` - Zone detail view
- `/emergency/` - Emergency reporting page
- `/emergency/dashboard/` - Emergency control center
- `/lost-person/` - Lost & Found reporting
- `/security/` - Security dashboard

### API Routes
- `/parking/api/check-in/` - Check-in to a parking slot
- `/parking/api/check-out/` - Check-out from a parking slot
- `/parking/api/release-slot/` - Release a parking slot
- `/emergency/api/submit/` - Submit emergency report
- `/emergency/api/list/` - List emergency reports
- `/emergency/api/update-status/` - Update emergency status
- `/parking/api/lost-found/submit/` - Submit lost/found report
- `/parking/api/lost-found/list/` - List lost/found reports
- `/parking/api/lost-found/update-status/` - Update lost/found status

## 🎨 UI/UX Features

### Design System
- **Modern SaaS-style UI**: Clean, professional interface
- **Dark Theme**: Eye-friendly dark background with glass morphism effects
- **Typography**: DM Sans, Space Grotesk, and DM Mono fonts
- **Color Palette**: Consistent color scheme with semantic colors
- **Responsive Design**: Fully responsive for mobile, tablet, and desktop

### Interactive Elements
- **Animated Orbs**: Background decorative elements
- **Glass Cards**: Frosted glass effect for cards
- **Pulse Animations**: For live indicators and SOS button
- **Hover Effects**: Smooth transitions on interactive elements
- **Toast Notifications**: Non-intrusive success/error messages
- **Loading Spinners**: Visual feedback during async operations

### Mobile Responsiveness
All pages are fully responsive with:
- Stacked layouts on mobile
- Touch-friendly buttons and inputs
- Optimized font sizes and spacing
- Mobile-specific navigation adjustments

## 🔧 Management Commands

### Seed Parking Zones
Create initial parking zones with slots:
```bash
python manage.py seed_parking_zones
```

### Release Expired Slots
Manually release expired parking sessions:
```bash
python manage.py release_expired_slots
```

## 📊 Admin Panel

Access the Django admin panel at `/admin/` to:
- Manage parking zones and slots
- View and manage emergency reports
- View and manage lost/found reports
- Monitor system activity

## 🧪 Testing

Run tests with:
```bash
python manage.py test
```

## 🚀 Deployment

### Production Checklist

1. **Set DEBUG to False** in `ParkEase/settings.py`
2. **Set ALLOWED_HOSTS** to your domain
3. **Generate a secure SECRET_KEY**
4. **Configure production database**
5. **Collect static files**: `python manage.py collectstatic`
6. **Set up a production web server** (Gunicorn, uWSGI)
7. **Configure reverse proxy** (Nginx, Apache)
8. **Set up media file serving**
9. **Enable HTTPS**
10. **Configure logging**

### Gunicorn Example
```bash
pip install gunicorn
gunicorn ParkEase.wsgi:application --bind 0.0.0.0:8000
```

## 🛠️ Troubleshooting

### Common Issues

**Migration Errors**
```bash
# Reset migrations (WARNING: Deletes data)
python manage.py migrate --fake-initial
python manage.py migrate
```

**Static Files Not Loading**
```bash
# Collect static files
python manage.py collectstatic
```

**Database Locked**
```bash
# Delete database and re-migrate
rm db.sqlite3
python manage.py migrate
```

**Port Already in Use**
```bash
# Run on different port
python manage.py runserver 8080
```

## 📝 Technologies Used

- **Backend**: Django 5.0
- **Database**: SQLite (default), PostgreSQL/MySQL supported
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Custom CSS with CSS Grid and Flexbox
- **Icons**: Font Awesome 6.5.0
- **Fonts**: Google Fonts (DM Sans, Space Grotesk, DM Mono)
- **Image Processing**: Pillow

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 📞 Support

For issues or questions:
- Check the troubleshooting section
- Review Django documentation: https://docs.djangoproject.com/
- Check the admin panel for detailed error logs

## 🎯 Future Enhancements

Potential features for future versions:
- User authentication and authorization
- Email notifications for emergencies
- SMS integration for emergency alerts
- Mobile app (React Native/Flutter)
- Real-time WebSocket updates
- Advanced analytics and reporting
- Multi-language support
- Payment integration for parking fees
- License plate recognition
- IoT sensor integration

---

**Built with Django 5.0** | **Responsive Design** | **Modern UI/UX**
