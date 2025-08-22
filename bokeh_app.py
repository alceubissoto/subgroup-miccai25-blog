import os, random, re
import numpy as np
import pandas as pd
from PIL import Image
from bokeh.plotting import figure
from bokeh.transform import transform
from bokeh.models import (
    ColumnDataSource, CDSView, GroupFilter,
    LinearColorMapper, CategoricalColorMapper,
    ColorBar, HoverTool, Legend, LegendItem, Select, Button, Div
)
from bokeh.layouts import column, row
from bokeh.palettes import inferno, Turbo256
from sklearn.metrics import accuracy_score, balanced_accuracy_score

# -------------- Data Loading --------------
bias_level, model_type = "0.6", "clip"
dict_models = {"0.6":"stoic-energy-14","0.7":"vital-pond-23",
               "0.8":"unique-glitter-24","0.9":"ancient-sky-25"}

output_csv  = f"static/susu_ERM_hypertag_{dict_models[bias_level]}_test_tsne_{model_type}_metadata.csv"
subgroup_csv = "static/results_persample_l3_valtest_clip_imagenet_w10.csv"

# Convert full paths to tail format for merging and image serving
def to_tail(path):
    if not isinstance(path, str) or not path:
        return ""
    m = re.search(r"(train|val|test)/.*$", path)
    return m.group(0) if m else os.path.basename(path)

# Load data with seed=0 filter for subgroups
metadata_df = pd.read_csv(output_csv)
subgroup_df = pd.read_csv(subgroup_csv)

# CRITICAL: Only use seed=0 AND split='test' rows from subgroups file (to match t-SNE)
subgroup_df = subgroup_df[(subgroup_df['seed'] == 0) & (subgroup_df['split'] == 'test')]

# Convert metadata paths to tail format for matching with subgroup data
metadata_df['name_tail'] = metadata_df['name'].apply(to_tail)

# Merge on the tail paths
df = pd.merge(metadata_df, subgroup_df, "inner", left_on="name_tail", right_on="name")

# Keep both original name and tail path
df['image_path'] = df['name_tail']

# Load available images - but DON'T filter the main dataframe yet
image_list_files = ['static/image_list_representative.txt', 'static/image_list.txt']
available_images = set()

for image_file in image_list_files:
    try:
        with open(image_file, 'r') as f:
            available_images.update(line.strip() for line in f if line.strip())
        print(f"Loaded images from {image_file}")
        break
    except FileNotFoundError:
        continue

if not available_images:
    print("Warning: No image list found, using all images")
else:
    print(f"Total available images for grid display: {len(available_images)}")

# Add flag to mark which samples have available images (for grid display)
df['has_image'] = df['image_path'].isin(available_images)

df.rename(columns={"sex": "Sex", "race": "Race", 'ethnicity' : "Ethnicity",
                   'insurance_type':'Insurance Type', 'interpreter_needed':'Interpreter Needed',
                   'true_subgroup_idx':'(Hidden) Artifacts', 'discovered_subgroup_idx':'(Ours) Found Subgroups' }, inplace=True)

metadata_cols = ['Sex', 'Race', 'Support Devices', 'Lung Lesion', 'Cardiomegaly', '(Ours) Found Subgroups']
# Filter to only include columns that exist in the dataframe
metadata_cols = [col for col in metadata_cols if col in df.columns]

for col in ['Lung Lesion','Edema','Fracture','Support Devices',
            'No Finding','(Hidden) Artifacts','(Ours) Found Subgroups']:
    if col in df.columns:
        df[col] = df[col].astype(str)

source = ColumnDataSource({**{c: df[c] for c in ['x','y','name','image_path','has_image'] if c in df.columns},
                           **{c: df[c].astype(str)
                              if df[c].dtype=='object' else df[c]
                              for c in metadata_cols if c in df.columns}})

# --- Helper for color mapping ---
def create_color_mapper(col):
    if col not in df.columns:
        return LinearColorMapper(palette=Turbo256, low=0, high=1, nan_color='gray'), None, col, None
    if df[col].dtype == 'object':
        factors = sorted([str(x) for x in df[col].unique()])
        palette = inferno(len(factors))
        return CategoricalColorMapper(palette=palette, factors=factors, nan_color='gray'), None, col, factors
    else:
        low, high = df[col].min(), df[col].max()
        return LinearColorMapper(palette=Turbo256, low=low, high=high, nan_color='gray'), None, col, None

# ----------- Bokeh app function -------------
def modify_doc(doc):

    # Initial dropdowns
    attr_select = Select(title="Color by", value=metadata_cols[0], options=metadata_cols)
    value_select = Select(title="Isolate class", value="All", options=["All"])
    calc_button = Button(label="🔍 Analyze Performance", button_type="primary")
    perf_div = Div(text="", width=400, height=120)
    grid_div = Div(text="", width=600)

    # --- Main t-SNE plot setup ---
    color_mapper, color_bar, field_name, factors = create_color_mapper(attr_select.value)
    p = figure(title="t-SNE Visualization",
           tools="pan,wheel_zoom,box_zoom,reset,tap,box_select,lasso_select",
           width=600, height=500, sizing_mode="scale_width", max_width=600)
    p.xgrid.visible = False
    p.ygrid.visible = False
    p.xaxis.visible = False
    p.yaxis.visible = False

    _, _, field_name, factors = create_color_mapper(attr_select.value)
    if factors:
        value_select.options = ["All"] + list(factors)
        value_select.value = "All"
    else:
        value_select.options = ["All"]
        value_select.value = "All"
        
    # Glyphs
    renderers = []
    if factors:
        for fac, col in zip(factors, color_mapper.palette):
            view = CDSView(source=source, filters=[GroupFilter(column_name=field_name, group=fac)])
            r = p.circle('x', 'y', size=5, source=source, view=view,
                         alpha=0.2, color=col, muted_alpha=0)
            renderers.append(r)
        p.add_layout(Legend(items=[LegendItem(label=str(f), renderers=[r])
                                   for f, r in zip(factors, renderers)],
                            title=attr_select.value, orientation="horizontal", nrows=2,
                            click_policy="mute"), 'above')
    else:
        r = p.circle('x','y',size=5,source=source,alpha=0.2,
                     fill_color=transform(field_name, color_mapper), muted_alpha=0)
        if color_bar is not None:
            p.add_layout(color_bar, 'right')
        renderers.append(r)

    hover = HoverTool(tooltips=[("Value", f"@{field_name}")])
    p.add_tools(hover)

    # --- Helper: Update value_select when attribute changes ---
    def update_value_select(attr, old, new):
        nonlocal renderers, field_name, color_mapper
        color_mapper, _, field_name, factors = create_color_mapper(attr_select.value)
        # Clear old renderers/legends
        p.renderers = [r for r in p.renderers if r not in renderers]
        for pos in ['left', 'right', 'above', 'below', 'center']:
            items = getattr(p, pos)
            items[:] = [i for i in items if not isinstance(i, Legend)]

        renderers.clear()
        if factors:
            value_select.options = ["All"] + list(factors)
            value_select.value = "All"
            for fac, col in zip(factors, color_mapper.palette):
                view = CDSView(source=source, filters=[GroupFilter(column_name=field_name, group=fac)])
                r = p.circle('x', 'y', size=5, source=source, view=view,
                             alpha=0.2, color=col, muted_alpha=0)
                renderers.append(r)
            p.add_layout(Legend(items=[LegendItem(label=str(f), renderers=[r])
                                       for f, r in zip(factors, renderers)],
                                title=attr_select.value, orientation="horizontal", nrows=2,
                                click_policy="mute"), 'above')
        else:
            value_select.options = ["All"]
            value_select.value = "All"
            r = p.circle('x','y',size=5,source=source,alpha=0.2,
                         fill_color=transform(field_name, color_mapper), muted_alpha=0)
            renderers.append(r)
        hover.tooltips = [("Value", f"@{field_name}")]

    attr_select.on_change('value', update_value_select)

    # --- Helper: Solo class visibility ---
    def update_visible(attr, old, new):
        selected = value_select.value
        if selected == "All":
            for r in renderers:
                r.visible = True
        else:
            for r, fac in zip(renderers, value_select.options[1:]):
                r.visible = (fac == selected)

    value_select.on_change('value', update_visible)

    # --- Helper: Get visible indices for current selection ---
    def get_visible_indices():
        # Return list of indices that are currently visible (used for performance/image grid)
        selected = value_select.value
        if selected == "All" or not factors:
            return list(range(len(df)))
        else:
            return list(np.where(df[field_name].astype(str) == selected)[0])

    # --- Helper: Button callback to calculate performance and show images ---
    def on_calc():
        idx = get_visible_indices()
        
        # Performance metrics (using all visible samples)
        y_true_all = df['y_true']
        y_pred_all = (df['y_pred'] >= 0.5)
        y_true_sub = df.loc[idx, 'y_true']
        y_pred_sub = (df.loc[idx, 'y_pred'] >= 0.5)
        acc_all = accuracy_score(y_true_all, y_pred_all)
        acc_sub = accuracy_score(y_true_sub, y_pred_sub) if len(idx) else float('nan')
        bacc_all = balanced_accuracy_score(y_true_all, y_pred_all)
        bacc_sub = balanced_accuracy_score(y_true_sub, y_pred_sub) if len(idx) else float('nan')

        perf_div.text = f"""
            <div style='
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 10px 0;
            '>
                <div style='
                    background: linear-gradient(135deg, #0065bd, #004a9f);
                    color: white;
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(0,101,189,0.25);
                '>
                    <div style='font-size: 13px; opacity: 0.85; margin-bottom: 8px; text-transform: uppercase; font-weight: 500; letter-spacing: 0.5px;'>Whole Dataset</div>
                    <div style='font-size: 18px; font-weight: 700; margin-bottom: 4px;'>ACC: {acc_all:.3f}</div>
                    <div style='font-size: 18px; font-weight: 700;'>bACC: {bacc_all:.3f}</div>
                </div>
                <div style='
                    background: linear-gradient(135deg, #dc2626, #b91c1c);
                    color: white;
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(220,38,38,0.25);
                '>
                    <div style='font-size: 13px; opacity: 0.85; margin-bottom: 8px; text-transform: uppercase; font-weight: 500; letter-spacing: 0.5px;'>Selected Subset (n={len(idx)})</div>
                    <div style='font-size: 18px; font-weight: 700; margin-bottom: 4px;'>ACC: {acc_sub:.3f}</div>
                    <div style='font-size: 18px; font-weight: 700;'>bACC: {bacc_sub:.3f}</div>
                </div>
            </div>
        """

        # REPRESENTATIVE IMAGE SAMPLING for current category/value
        selected = value_select.value
        current_category = attr_select.value
        
        if selected == "All" or not factors:
            # For "All", sample from available images across all values
            available_subset = df[df['has_image']].copy()
            if len(available_subset) > 12:
                sample_imgs = available_subset.sample(12, random_state=42)['image_path'].tolist()
            else:
                sample_imgs = available_subset['image_path'].tolist()
        else:
            # For specific value, sample ONLY from that category value (with available images)
            category_subset = df[(df[current_category].astype(str) == selected) & df['has_image']].copy()
            
            if len(category_subset) == 0:
                sample_imgs = []
            elif len(category_subset) <= 12:
                sample_imgs = category_subset['image_path'].tolist()
            else:
                # Representative sampling: ensure diversity across other attributes
                sample_imgs = category_subset.sample(12, random_state=42)['image_path'].tolist()
                
        # Generate HTML grid
        html = f"""
            <div style='
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 10px;
            '>
        """
        
        image_count = 0
        for img in sample_imgs[:12]:
            if img and image_count < 12:  # Only show if image path exists
                html += f"<img src='/static/{img}' style='width:120px;height:120px;margin:2px;object-fit:cover;border-radius:7px;border:1px solid #ccc;' title='{img}'/>"
                image_count += 1
                
        # Fill remaining slots with placeholders if needed
        while image_count < 12:
            html += "<div style='width:120px;height:120px;margin:2px;border:1px dashed #ccc;border-radius:7px;display:flex;align-items:center;justify-content:center;color:#999;font-size:12px;'>No Image</div>"
            image_count += 1
            
        html += "</div>"
        
        # Remove debug text - keep it clean
            
        grid_div.text = html

    calc_button.on_click(on_calc)

    # --- Layout ---
    # Clean controls layout without extra boxes
    controls = row(attr_select, value_select, calc_button, sizing_mode="stretch_width")
    
    # Right panel with just the performance metrics and image grid
    right_panel = column(
        perf_div,
        grid_div,
        sizing_mode="stretch_width"
    )
    
    # Enhanced button styling
    calc_button.button_type = "primary"
    calc_button.sizing_mode = "stretch_width"
    
    # Enhanced controls styling with aligned elements
    enhanced_controls = column(
        controls,
        sizing_mode="stretch_width"
    )
    
    # Main layout with better organization
    doc.add_root(column(
        enhanced_controls,
        row(p, right_panel, sizing_mode="stretch_width"),
        sizing_mode="stretch_width"
    ))

def create_plot():
    """Create a static plot for embedding without server"""
    # Debug: print available columns
    print("Available columns:", list(df.columns))
    
    # Create basic t-SNE plot
    p = figure(
        width=500, height=500,
        x_axis_label="t-SNE 1",
        y_axis_label="t-SNE 2",
        title="Subgroup Performance Analysis",
        toolbar_location="above"
    )
    
    # Check what subgroup column exists
    subgroup_col = None
    for col in ['discovered_subgroup_idx', 'subgroup_idx', 'subgroup']:
        if col in df.columns:
            subgroup_col = col
            break
    
    # Use subset for performance
    plot_df = df.sample(min(1000, len(df)), random_state=42)
    source = ColumnDataSource(plot_df)
    
    if subgroup_col:
        # Add t-SNE points colored by discovered subgroups
        unique_subgroups = plot_df[subgroup_col].nunique()
        color_mapper = LinearColorMapper(palette=inferno(max(3, unique_subgroups)), 
                                       low=plot_df[subgroup_col].min(), 
                                       high=plot_df[subgroup_col].max())
        
        p.circle('x', 'y', size=3, source=source, alpha=0.6,
                 color=transform(subgroup_col, color_mapper))
        
        # Add color bar
        color_bar = ColorBar(color_mapper=color_mapper, width=8, location=(0,0),
                            title="Discovered Subgroup")
        p.add_layout(color_bar, 'right')
        
        # Add hover tool
        hover = HoverTool(tooltips=[
            ("Subgroup", f"@{subgroup_col}"),
            ("Sex", "@sex"),
            ("Race", "@race")
        ])
    else:
        # Fallback: color by sex if no subgroup column
        p.circle('x', 'y', size=3, source=source, alpha=0.6, color='blue')
        
        hover = HoverTool(tooltips=[
            ("Sex", "@sex"),
            ("Race", "@race")
        ])
    
    p.add_tools(hover)
    
    return p
