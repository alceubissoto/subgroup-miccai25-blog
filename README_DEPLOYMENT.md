# Subgroup Performance Analysis - Deployment Guide

This project supports multiple deployment options to accommodate different needs and preferences.

## 🚀 Quick Start Options

### Option 1: Streamlit (Recommended ✅)

**Local Development:**
```bash
# Install dependencies
pip install -r requirements_streamlit.txt

# Run locally
python run_local.py streamlit
# OR directly: streamlit run streamlit_app.py
```

**Fly.io Deployment:**
```bash
# Deploy to Fly.io
fly deploy -c fly.streamlit.toml

# Monitor logs
fly logs -a subgroup-streamlit-blog
```

**Why Streamlit?**
- ✅ Simpler deployment (no port conflicts)
- ✅ Better Bokeh integration
- ✅ Built-in responsive design
- ✅ Easier to maintain
- ✅ Fast iterations

### Option 2: Flask (Original)

**Local Development:**
```bash
# Install dependencies  
pip install -r requirements.txt

# Run locally
python run_local.py flask
# OR directly: python app.py
```

**Fly.io Deployment:**
```bash
# Deploy to Fly.io
fly deploy  # Uses fly.toml
```

## 📊 Feature Comparison

| Feature | Flask Version | Streamlit Version |
|---------|--------------|-------------------|
| Interactive t-SNE | ❌ Static plot only | ✅ Full interactivity |
| Dropdown controls | ❌ Missing | ✅ Working |
| Performance calculation | ❌ Missing | ✅ Working |
| Image grid display | ❌ Missing | ✅ Working |
| Deployment complexity | ❌ High (port issues) | ✅ Simple |
| Local development | ✅ Works | ✅ Works |
| Responsive design | ⚠️ Basic | ✅ Built-in |

## 🔧 Development Workflow

### Local Testing
```bash
# Test Streamlit version (recommended)
python run_local.py streamlit

# Test Flask version  
python run_local.py flask
```

### Data Preparation
```bash
# Generate asset file list (if needed)
python prepare_assets.py --per-value 12 --output static/image_list.txt

# Download images using rsync
rsync --files-from=static/image_list.txt /source/path/ static/images/
```

## 🐳 Docker Options

### Streamlit Docker
```bash
# Build
docker build -f Dockerfile.streamlit -t subgroup-streamlit .

# Run locally
docker run -p 8501:8501 subgroup-streamlit
```

### Flask Docker (original)
```bash
# Build  
docker build -t subgroup-flask .

# Run locally
docker run -p 8080:8080 subgroup-flask
```

## 🌐 Deployment Platforms

### Fly.io (Recommended)
```bash
# Streamlit version
fly deploy -c fly.streamlit.toml

# Flask version
fly deploy -c fly.toml
```

### Streamlit Cloud
1. Push code to GitHub
2. Connect repository to Streamlit Cloud
3. Set main file path: `streamlit_app.py`
4. Deploy automatically

### Other Options
- **Heroku**: Both versions work
- **Railway**: Streamlit preferred
- **Render**: Both supported
- **DigitalOcean**: Docker deployment

## 🔍 Troubleshooting

### Common Issues

**Flask Port Conflicts:**
- Solution: Use Streamlit version instead

**Missing Column Errors:**
- Check data files are in `static/` directory
- Verify CSV files have correct structure
- Check logs for column debug info

**Image Loading Issues:**
- Ensure images are in `static/` directory
- Check `static/image_list.txt` exists
- Verify rsync completed successfully

**Bokeh JavaScript Errors:**
- Streamlit handles this automatically
- Flask version needs CDN links in template

### Environment Variables

For production deployments:

**Streamlit:**
```bash
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

**Flask:**
```bash
FLASK_ENV=production
PORT=8080
```

## 📈 Performance Tips

1. **Data Caching**: Streamlit automatically caches data loading
2. **Image Optimization**: Consider serving images from CDN
3. **Subsampling**: Large datasets are automatically subsampled for visualization
4. **Memory**: 1GB RAM should be sufficient for both versions

## 🎯 Recommendation

**For new deployments**: Use Streamlit version
**For existing Flask deployments**: Consider migrating to Streamlit

The Streamlit version provides all the interactive features that were missing in the simplified Flask version, with much easier deployment.