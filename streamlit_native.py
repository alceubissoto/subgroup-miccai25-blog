import streamlit as st
import os, random, re
import numpy as np
import pandas as pd
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import accuracy_score, balanced_accuracy_score

# Page config
st.set_page_config(
    page_title="Subgroup Performance Analysis",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.main {
    padding-top: 2rem;
}
.instructions {
    background: linear-gradient(135deg, #e8f4fd, #f0f9ff);
    border: 1px solid #0ea5e9;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 25px;
    color: #0c4a6e;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
}
/* Make sidebar narrower */
.css-1d391kg {
    width: 250px !important;
}
/* Improve image grid spacing */
.stImage > img {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and process data with caching"""
    # Data Loading
    bias_level, model_type = "0.6", "clip"
    dict_models = {"0.6":"stoic-energy-14","0.7":"vital-pond-23",
                   "0.8":"unique-glitter-24","0.9":"ancient-sky-25"}
    
    output_csv = f"static/susu_ERM_hypertag_{dict_models[bias_level]}_test_tsne_{model_type}_metadata.csv"
    subgroup_csv = "static/results_persample_l3_valtest_clip_imagenet_w10.csv"
    
    # Convert full paths to tail format for merging and image serving
    def to_tail(path):
        if not isinstance(path, str) or not path:
            return ""
        m = re.search(r"(train|val|test)/.*$", path)
        return m.group(0) if m else os.path.basename(path)
    
    try:
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
        
        # Load available images
        image_list_files = ['static/image_list_representative.txt', 'static/image_list.txt']
        available_images = set()
        
        for image_list_file in image_list_files:
            if os.path.exists(image_list_file):
                with open(image_list_file, 'r') as f:
                    available_images.update(line.strip() for line in f if line.strip())
        
        # Map NaN values to "0" for clinical attributes (missing/uncertain)
        clinical_cols = ['Support Devices', 'Lung Lesion', 'Cardiomegaly']
        for col in clinical_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # Data loaded successfully
        
        return df, available_images
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), set()

def create_tsne_plot(df, color_attr, filter_value=None):
    """Create t-SNE plot with Plotly"""
    plot_df = df.copy()
    original_df = df.copy()
    
    # Apply filtering if specified
    if filter_value and filter_value != "All":
        if color_attr not in plot_df.columns:
            st.error(f"Column '{color_attr}' not found in data")
            return None
        
        try:
            unique_vals = plot_df[color_attr].dropna().unique()
            
            if len(unique_vals) > 0:
                sample_val = unique_vals[0]
                
                if isinstance(sample_val, (int, float, np.integer, np.floating)):
                    if '.' in str(filter_value):
                        filter_val_converted = float(filter_value)
                    else:
                        try:
                            filter_val_converted = int(filter_value)
                        except ValueError:
                            filter_val_converted = float(filter_value)
                else:
                    filter_val_converted = str(filter_value)
                
                plot_df = plot_df[plot_df[color_attr] == filter_val_converted]
            else:
                return None
            
        except (ValueError, IndexError):
            return None
    
    # Subsample for performance
    if len(plot_df) > 3000:
        plot_df = plot_df.sample(3000, random_state=42)
    
    if len(plot_df) == 0:
        st.warning("No data to display with current filters")
        return None
    
    # Check required columns
    if 'x' not in plot_df.columns or 'y' not in plot_df.columns or color_attr not in plot_df.columns:
        st.error(f"Required columns missing")
        return None
    
    # Create hover data
    hover_cols = ['sex', 'race', 'image_path']
    hover_data = {}
    for col in hover_cols:
        if col in plot_df.columns:
            hover_data[col] = True
    
    try:
        # Determine if categorical
        unique_values_orig = original_df[color_attr].dropna().nunique()
        is_categorical = (unique_values_orig <= 20 or 
                         color_attr in ['discovered_subgroup_idx', 'subgroup_idx', 'subgroup'] or
                         not pd.api.types.is_numeric_dtype(original_df[color_attr]))
        
        if is_categorical:
            # Handle missing values and convert to string
            plot_df = plot_df.dropna(subset=[color_attr])
            if len(plot_df) == 0:
                st.warning("No valid data after removing missing values")
                return None
            plot_df[color_attr] = plot_df[color_attr].astype(str)
            
            # Get all unique values for consistent coloring
            unique_vals_clean = original_df[color_attr].dropna()
            if len(unique_vals_clean) == 0:
                st.error(f"No valid values found in column '{color_attr}'")
                return None
            all_unique_values = sorted(unique_vals_clean.astype(str).unique())
            
            # Use more visible colors
            bright_colors = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
                '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
            ]
            
            if len(all_unique_values) > len(bright_colors):
                bright_colors = bright_colors * ((len(all_unique_values) // len(bright_colors)) + 1)
            
            color_map = {val: bright_colors[i % len(bright_colors)] for i, val in enumerate(all_unique_values)}
            
            # Create plot with fixed legend width
            fig = go.Figure()
            
            for value in plot_df[color_attr].unique():
                mask = plot_df[color_attr] == value
                subset = plot_df[mask]
                
                fig.add_trace(go.Scatter(
                    x=subset['x'],
                    y=subset['y'],
                    mode='markers',
                    marker=dict(
                        color=color_map[value],
                        size=6,
                        opacity=0.8,
                        line=dict(width=0.5, color='white')
                    ),
                    name=str(value),
                    hovertemplate='<br>'.join([f'{col}: %{{customdata[{i}]}}' for i, col in enumerate(hover_cols) if col in subset.columns]) + '<extra></extra>',
                    customdata=subset[[col for col in hover_cols if col in subset.columns]].values if hover_cols else None
                ))
            
            # Find the longest legend item to set fixed width
            max_legend_length = max(len(str(val)) for val in all_unique_values) if all_unique_values else 10
            legend_width = max(120, min(200, max_legend_length * 10))
            
            fig.update_layout(
                title=f"Colored by {color_attr.replace('_', ' ').title()}",
                xaxis_title="t-SNE Dimension 1",
                yaxis_title="t-SNE Dimension 2",
                font=dict(size=12),
                title_font_size=16,
                showlegend=True,
                plot_bgcolor='white',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.01,
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="rgba(0,0,0,0.1)",
                    borderwidth=1
                ),
                width=600 + legend_width,
                height=400,
                margin=dict(r=legend_width + 20)
            )
        else:
            # Continuous coloring
            fig = px.scatter(
                plot_df, 
                x='x', 
                y='y',
                color=color_attr,
                title=f"Colored by {color_attr.replace('_', ' ').title()}",
                hover_data=hover_data,
                width=700,
                height=400,
                color_continuous_scale='viridis'
            )
            
            fig.update_layout(
                xaxis_title="t-SNE Dimension 1",
                yaxis_title="t-SNE Dimension 2",
                font=dict(size=12),
                title_font_size=16,
                plot_bgcolor='white'
            )
            
            fig.update_traces(marker=dict(size=6, opacity=0.8))
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating plot: {e}")
        return None

def calculate_performance(df, filter_col, filter_val):
    """Calculate performance metrics for filtered data"""
    try:
        # Apply filtering
        if filter_val == "All":
            filtered_df = df
        else:
            if filter_col not in df.columns:
                return None, None, 0
            
            unique_vals = df[filter_col].dropna().unique()
            
            if len(unique_vals) > 0:
                sample_val = unique_vals[0]
                
                if isinstance(sample_val, (int, float, np.integer, np.floating)):
                    if '.' in str(filter_val):
                        filter_val_converted = float(filter_val)
                    else:
                        try:
                            filter_val_converted = int(filter_val)
                        except ValueError:
                            filter_val_converted = float(filter_val)
                else:
                    filter_val_converted = str(filter_val)
                
                filtered_df = df[df[filter_col] == filter_val_converted]
            else:
                return None, None, 0
        
        if len(filtered_df) == 0:
            return None, None, 0
        
        # Find prediction columns
        y_true_col = None
        y_pred_col = None
        
        for col in ['y_true', 'Cardiomegaly', 'cardiomegaly', 'label', 'target']:
            if col in filtered_df.columns:
                y_true_col = col
                break
                
        for col in ['y_pred', 'pred_Cardiomegaly', 'pred_cardiomegaly', 'prediction', 'pred']:
            if col in filtered_df.columns:
                y_pred_col = col
                break
        
        if y_true_col is None or y_pred_col is None:
            return None, None, len(filtered_df)
        
        # Calculate metrics
        y_true = filtered_df[y_true_col].values
        y_pred = filtered_df[y_pred_col].values
        
        # Remove NaN values
        mask = ~(pd.isna(y_true) | pd.isna(y_pred))
        y_true = y_true[mask]
        y_pred = y_pred[mask]
        
        if len(y_true) == 0:
            return None, None, len(filtered_df)
        
        # Convert predictions to binary
        y_pred_binary = y_pred > 0.5
            
        acc = accuracy_score(y_true, y_pred_binary)
        bal_acc = balanced_accuracy_score(y_true, y_pred_binary)
        
        return acc, bal_acc, len(filtered_df)
        
    except Exception as e:
        return None, None, 0

def display_sample_images(df, filter_col, filter_val, available_images, max_images=12):
    """Display sample images from filtered data"""
    try:
        # Apply filtering
        if filter_val == "All":
            filtered_df = df
        else:
            if filter_col not in df.columns:
                return
            
            unique_vals = df[filter_col].dropna().unique()
            
            if len(unique_vals) > 0:
                sample_val = unique_vals[0]
                
                if isinstance(sample_val, (int, float, np.integer, np.floating)):
                    if '.' in str(filter_val):
                        filter_val_converted = float(filter_val)
                    else:
                        try:
                            filter_val_converted = int(filter_val)
                        except ValueError:
                            filter_val_converted = float(filter_val)
                else:
                    filter_val_converted = str(filter_val)
                
                filtered_df = df[df[filter_col] == filter_val_converted]
            else:
                return
        
        # Get available images
        if 'image_path' not in filtered_df.columns:
            return
            
        available_filtered = filtered_df[filtered_df['image_path'].isin(available_images)]
        
        if len(available_filtered) == 0:
            st.warning("No images available for this selection")
            return
        
        # Sample images
        sample_size = min(max_images, len(available_filtered))
        sample_df = available_filtered.sample(sample_size, random_state=42)
        
        # Display in 6-column grid
        cols = st.columns(6)
        for i, (_, row) in enumerate(sample_df.iterrows()):
            col_idx = i % 6
            with cols[col_idx]:
                img_path = f"static/{row['image_path']}"
                if os.path.exists(img_path):
                    try:
                        img = Image.open(img_path)
                        img = img.convert('RGB')
                        img.thumbnail((180, 180), Image.Resampling.LANCZOS)
                        
                        square_img = Image.new('RGB', (180, 180), (240, 240, 240))
                        x_offset = (180 - img.width) // 2
                        y_offset = (180 - img.height) // 2
                        square_img.paste(img, (x_offset, y_offset))
                        
                        st.image(square_img, use_container_width=True)
                    except Exception:
                        pass
                        
    except Exception:
        pass

def main():
    # Header with proper blog styling (removed stethoscope)
    st.title("Subgroup Performance Analysis in Hidden Stratifications")
    
    # Authors
    st.markdown("""
    <div style="text-align:left; margin-bottom:2rem; color:#666; font-size:0.9em;">
    Alceu Bissoto¹'², Trung-Dung Hoang¹'², Tim Flühmann¹'², Susu Sun³, Christian F Baumgartner³'⁴, Lisa M Koch¹'²<br>
    <span style="font-size:0.8em;">
    ¹ UDEM, Inselspital, University of Bern, Switzerland | ² Diabetes Center Berne, Switzerland<br>
    ³ University of Tübingen, Germany | ⁴ University of Lucerne, Switzerland
    </span>
    </div>
    """, unsafe_allow_html=True)

    # Paper link
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:2rem;">
        <a href="https://arxiv.org/pdf/2503.10382" target="_blank" 
           style="background:#0066cc; color:white; padding:10px 20px; text-decoration:none; border-radius:8px; font-weight:500;">
        📄 View Paper
        </a>
        </div>
        """, unsafe_allow_html=True)

    # Introduction sections
    st.header("🎯 Does current AI evaluation capture the relevant characteristics in medical imaging?")
    
    st.markdown("""
    Traditional subgroup analysis, a common practice in medical research, often falls short when evaluating deep learning models for medical imaging. The metadata typically used—like patient demographics or image characteristics—frequently fails to identify the nuanced variations that truly affect AI performance.
    """)
    
    st.header("❓ Why does this matter?")
    
    st.markdown("""
    When assessing AI models, results are usually reported as averages across entire datasets. Although useful, this practice masks significant performance variations among specific groups. Clinical trials and medical AI studies often stratify results by demographic attributes (e.g., age, sex, or ethnicity), but AI medical models might not rely on these standard metadata categories, leading to suboptimal performance evaluations.

    Our latest research studies an alternative approach: using subgroup discovery methods to enrich performance analysis. Subgroup discovery methods uncover hidden patterns and systematic groupings beyond traditional metadata, providing deeper and more meaningful insights into AI model performance.
    """)
    
    # Add the demo explanation image if it exists
    if os.path.exists("static/demo_explanation.png"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("static/demo_explanation.png", caption="Explanation of subgroup discovery approach")

    # Interactive section
    st.header("🔬 Interactive Exploration: Unveiling Hidden Patterns")
    
    st.markdown("""
    <div class="instructions">
        <strong>💡 How to explore:</strong> We are investigating a model trained for **cardiomegaly detection** on chest X-rays. 
        Select different patient attributes from the sidebar (demographics, clinical conditions, or discovered subgroups). 
        Use the filter to focus on specific values to reveal performance metrics and view representative medical images from that subgroup.
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    df, available_images = load_data()
    
    if df.empty:
        st.error("Could not load data. Please check that the data files exist in the static/ directory.")
        st.stop()
    
    
    # Controls above the plot
    st.subheader("🎛️ Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Attribute selection - dynamically build from available columns
        attribute_options = {}
        
        # Check what columns exist and map them
        column_mappings = {
            "Sex": ["sex"],
            "Race": ["race"], 
            "Support Devices": ["Support Devices", "support_devices"],
            "Lung Lesion": ["Lung Lesion", "lung_lesion"],
            "View Type": ["frontal_lateral", "view_type"],
            "Discovered Subgroups": ["discovered_subgroup_idx", "subgroup_idx", "subgroup"]
        }
        
        for display_name, possible_cols in column_mappings.items():
            for col in possible_cols:
                if col in df.columns:
                    attribute_options[display_name] = col
                    break
        
        if not attribute_options:
            st.error("No recognized attribute columns found in the data")
            st.stop()
        
        selected_attr = st.selectbox(
            "Select Attribute",
            options=list(attribute_options.keys()),
            index=min(6, len(attribute_options)-1) if len(attribute_options) > 6 else 0
        )
    
    with col2:
        attr_column = attribute_options[selected_attr]
        
        # Value filter
        unique_values = ["All"] + sorted(df[attr_column].dropna().unique().astype(str).tolist())
        selected_value = st.selectbox(
            f"Filter by {selected_attr}",
            options=unique_values,
            index=0
        )
        
        # Auto-trigger analysis when values change (no button needed)

    # Tips for exploration (moved closer to plot)
    with st.expander("💡 Tips for Exploration"):
        st.markdown("""
        **Try these explorations:**
        - **Discovered Subgroups**: Explore subgroups 0-14, especially subgroups 5 and 10 which show interesting patterns
        - **Demographics**: Compare performance across different sex and race categories
        - **Clinical attributes**: Check how Support Devices and Lung Lesion affect performance
        - **View types**: Compare frontal vs lateral X-ray performance
        
        **What to look for:**
        - Performance gaps between subgroups
        - Clustering patterns in the t-SNE plot
        - Representative images that show visual differences
        - How discovered subgroups differ from demographic groupings
        """)
    
    # Interactive analysis - auto-triggered
    st.subheader("📊 Interactive Analysis")
    
    # Calculate both overall and subgroup performance automatically
    overall_acc, overall_bal_acc, overall_count = calculate_performance(df, attr_column, "All")
    subgroup_acc, subgroup_bal_acc, subgroup_count = calculate_performance(df, attr_column, selected_value)
    
    # Top row: t-SNE plot and performance side by side
    plot_col, perf_col = st.columns([2, 1])
    
    with plot_col:
        fig = create_tsne_plot(df, attr_column, 
                              None if selected_value == "All" else selected_value)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    with perf_col:
        st.markdown("**📈 Performance Comparison**")
        
        # Display both performances vertically stacked
        if overall_acc is not None:
            st.markdown(f"""
            <div style="background:#f0f0f0; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                <h4>Overall Dataset</h4>
                <div><strong>Accuracy:</strong> {overall_acc:.3f}</div>
                <div><strong>Balanced Acc:</strong> {overall_bal_acc:.3f}</div>
                <div><small>Samples: {overall_count:,}</small></div>
            </div>
            """, unsafe_allow_html=True)
        
        if subgroup_acc is not None:
            st.markdown(f"""
            <div style="background:#e8f4fd; padding:1rem; border-radius:8px;">
                <h4>{selected_attr}: {selected_value}</h4>
                <div><strong>Accuracy:</strong> {subgroup_acc:.3f}</div>
                <div><strong>Balanced Acc:</strong> {subgroup_bal_acc:.3f}</div>
                <div><small>Samples: {subgroup_count:,}</small></div>
            </div>
            """, unsafe_allow_html=True)
    
    # Bottom row: Sample images spanning full width
    st.markdown("---")
    st.markdown("**🖼️ Sample Images**")
    display_sample_images(df, attr_column, selected_value, available_images)

    # Conclusion sections
    st.header("🔍 Key Findings from Our Study")
    
    st.markdown("""
    Our evaluation focused on two richly annotated medical imaging datasets: chest X-rays in **CheXpertPlus** and skin lesions in **SLICE3D**. The results were striking—subgroups discovered directly from data revealed significantly larger performance gaps compared to traditional metadata-based groups. We invite you to personally explore these metadata and newly discovered subgroups in our visualization (**Hint: Don't miss subgroups 5 and 10!**).

    Notably, the discovered subgroups often didn't correspond closely with patient demographics. Instead, they consistently aligned with meaningful visual features, such as lesion size and color in skin images.
    """)
    
    st.header("🚀 Implications for Real-World AI Deployment")
    
    st.markdown("""
    Given these insights, we argue that subgroup discovery is critical for robust AI model evaluation. It should complement traditional subgroup analysis, serving as an essential performance-monitoring tool during real-world validation and deployment of AI systems. Adopting subgroup discovery can significantly improve transparency, fairness, and reliability in medical AI.
    """)

if __name__ == "__main__":
    main()