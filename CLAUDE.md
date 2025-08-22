# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask/Bokeh web application for exploring subgroup performance analysis in medical imaging AI models. The project creates an interactive visualization blog post demonstrating hidden stratifications in AI model performance on chest X-ray datasets (CheXpertPlus) and their impact on fairness and reliability.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask application (serves both Flask frontend and Bokeh visualization)
python app.py
```
The app runs on `http://localhost:9000` by default and embeds a Bokeh server on port 5100.

### Data Preparation
```bash
# Generate asset file list for rsync (samples images for all categories)
python prepare_assets.py --per-value 12 --output static/image_list.txt

# The script automatically uses both data files:
# - static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv (demographics/clinical)
# - static/results_persample_l3_valtest_clip_imagenet_w10.csv (discovered subgroups)

# Download images using the generated list
rsync --files-from=static/image_list.txt /source/path/ static/images/
```

## Architecture

### Application Structure
- **Flask App (`app.py`)**: Main web server that serves the HTML template and embeds the Bokeh visualization
- **Bokeh App (`bokeh_app.py`)**: Interactive data visualization using Bokeh library for exploring subgroups and model performance
- **Data Preparation (`prepare_assets.py`)**: Utility script for sampling representative images across different demographic and clinical categories
- **Frontend (`templates/index.html`)**: Blog-style HTML template with embedded Bokeh visualization

### Data Flow
1. **Data Loading**: CSV files in `static/` contain model predictions, subgroup assignments, and metadata
2. **Visualization**: Bokeh app loads the data and creates interactive plots showing performance across different subgroups
3. **Image Display**: Medical images are served from `static/images/` directory with nested folder structure

### Key Data Files
- `static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv`: Main metadata with demographics, clinical labels, and full image paths (22,281 samples)
- `static/results_persample_l3_valtest_clip_imagenet_w10.csv`: Model results with discovered subgroup assignments (890,880 samples)
- `static/results_persample_hypertag_valtest_0.6_clip_imagenet_nslices15_weight10.csv`: Additional results file

**Data Structure**:
- Metadata file uses full paths in `name` column (e.g., `/storage/research/med_mlm/data/...`)
- Results file uses relative paths in `name` column (e.g., `train/patient123/study1/view1_frontal.png`)
- The `prepare_assets.py` script extracts the `train/val/test/...` portion for rsync compatibility

### Bokeh App Structure
The Bokeh application (when properly implemented) includes:
- Interactive subgroup selection widgets
- Performance visualization plots (accuracy, balanced accuracy)
- Image grid displays for selected subgroups
- t-SNE visualization with overlaid performance metrics
- Dropdown menus for filtering by patient attributes (sex, race, frontal/lateral view)

### Categories and Subgroups
The system analyzes medical imaging performance across:
- **Demographic**: sex (3 values: Male/Female/Unknown), race (8 values: White/Black/Asian/etc.)
- **Clinical**: Support Devices (3 values: -1/0/1), Lung Lesion (3 values), Cardiomegaly (3 values)
- **Technical**: frontal_lateral (2 values: Frontal/Lateral view orientation)
- **Discovered**: discovered_subgroup_idx (15 subgroups: 0-14, algorithmically identified)

**Sample Distribution**: The `prepare_assets.py` script samples up to 12 images per category value, resulting in ~434 unique images total. Some categories like "Support Devices" have limited samples (minimum 5) for certain values.

### File Status and Testing
✅ **Status**: The `bokeh_app.py` file has been restored and enhanced with:
- Proper image path handling using `static/image_list.txt`
- **Fixed**: Index reset after filtering to prevent KeyError on grid display
- Responsive side-by-side layout (t-SNE plot + performance/grid panel)  
- Multiple attribute categories: Sex, Race, Support Devices, Lung Lesion, Cardiomegaly, Discovered Subgroups
- Image validation testing with `test_image_validation.py`

**Testing**: Run `python test_image_validation.py` to verify that displayed images match selected demographic attributes.

**Image Directory**: Downloaded images are placed in `static/` following the paths in `static/image_list.txt` (e.g., `static/train/patient123/study1/view1_frontal.png`)

## Deployment Notes

- Uses port 9000 for Flask and port 5100 for Bokeh server
- Configured for Docker/Fly.io deployment with host="0.0.0.0"
- WebSocket origins configured for localhost development
- Static images served from nested directory structure under `static/images/`

## Research Context

This application supports the paper "Subgroup Performance Analysis in Hidden Stratifications" (MICCAI 2025) by demonstrating how subgroup discovery methods can reveal performance disparities that traditional demographic analysis might miss.