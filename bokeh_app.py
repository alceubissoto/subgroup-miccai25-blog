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
subgroup_csv = f"static/results_persample_hypertag_valtest_{bias_level}_clip_imagenet_nslices15_weight10.csv"

df = pd.merge(pd.read_csv(output_csv),
              pd.read_csv(subgroup_csv), "inner", "name")

df.rename(columns={"sex": "Sex", "race": "Race", 'ethnicity' : "Ethnicity",
                   'insurance_type':'Insurance Type', 'interpreter_needed':'Interpreter Needed',
                   'true_subgroup_idx':'(Hidden) Artifacts', 'discovered_subgroup_idx':'(Ours) Found Subgroups' }, inplace=True)

metadata_cols = ['Race','(Ours) Found Subgroups']
# Add more options if needed, e.g. 'Sex', 'Ethnicity'...

for col in ['Lung Lesion','Edema','Fracture','Support Devices',
            'No Finding','(Hidden) Artifacts','(Ours) Found Subgroups']:
    if col in df.columns:
        df[col] = df[col].astype(str)

source = ColumnDataSource({**{c: df[c] for c in ['x','y','name'] if c in df.columns},
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
    calc_button = Button(label="Compute visible average", button_type="primary")
    perf_div = Div(text="", width=400, height=120)
    grid_div = Div(text="", width=600)

    # --- Main t-SNE plot setup ---
    color_mapper, color_bar, field_name, factors = create_color_mapper(attr_select.value)
    p = figure(title="t-SNE Visualization",
           tools="pan,wheel_zoom,box_zoom,reset,tap,box_select,lasso_select",
           height=800, sizing_mode="stretch_width")
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
        subset20 = idx[:20]  # For speed, only show first 20
        # Performance metrics
        y_true_all = df['y_true']
        y_pred_all = (df['y_pred'] >= 0.5)
        y_true_sub = df.loc[idx, 'y_true']
        y_pred_sub = (df.loc[idx, 'y_pred'] >= 0.5)
        acc_all = accuracy_score(y_true_all, y_pred_all)
        acc_sub = accuracy_score(y_true_sub, y_pred_sub) if len(idx) else float('nan')
        bacc_all = balanced_accuracy_score(y_true_all, y_pred_all)
        bacc_sub = balanced_accuracy_score(y_true_sub, y_pred_sub) if len(idx) else float('nan')

        perf_div.text = (
            "<b>Performance Metrics (thr 0.5)</b><br>"
            f"<span style='color:#0065bd;'>Whole dataset:</span><br>"
            f"ACC: <b>{acc_all:.3f}</b> <br> bACC: <b>{bacc_all:.3f}</b><br>"
            f"<span style='color:#c60f13;'>Visible subset (n={len(idx)}):</span><br>"
            f"ACC: <b>{acc_sub:.3f}</b> <br> bACC: <b>{bacc_sub:.3f}</b><br>"
        )

        # Images: use relative path from Flask's /static/images/
        sample_imgs = [df.iloc[i]['name'] for i in subset20]
        html = """
            <div style='
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            '>
        """
        for img in sample_imgs[:18]:
            html += f"<img src='/static/images/{img}' style='width:120px;height:120px;margin:2px;object-fit:cover;border-radius:7px;border:1px solid #ccc;'/>"
        html += "</div>"
        grid_div.text = html

    calc_button.on_click(on_calc)

    # --- Layout ---
    controls = row(attr_select, value_select, calc_button, sizing_mode="stretch_width")
    doc.add_root(column(
        controls,
        p,
        perf_div,
        Div(text="<b>Random samples:</b>"),
        grid_div,
        sizing_mode="stretch_width"
    ))
