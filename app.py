import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
import math

# Page config
st.set_page_config(
    page_title="Công Cụ Tính Lấy Mẫu Kiểm Lùi - QA Tool",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("🔍 Công Cụ Tính Toán Lấy Mẫu Kiểm Lùi")
st.markdown("""
**Mục đích**: Xác định số lượng mẫu cần kiểm tra liên tục không phát hiện lỗi để release lô hàng đã sản xuất trước đó.

Công cụ này dựa trên:
- ISO 2859-1:2020 (Acceptance sampling)
- Lý thuyết thống kê Binomial và Hypergeometric
- Nguyên tắc OC Curve (Operating Characteristic)
""")

# Sidebar for inputs
st.sidebar.header("📝 Thông Số Đầu Vào")

# Input parameters
actual_defect_rate = st.sidebar.number_input(
    "Tỷ lệ lỗi thực tế phát hiện (%)",
    min_value=0.0,
    max_value=100.0,
    value=3.33,
    step=0.01,
    help="Ví dụ: Kiểm 30 gói, phát hiện 1 lỗi = 3.33%"
)

aql_level = st.sidebar.number_input(
    "AQL - Mức chất lượng chấp nhận (%)",
    min_value=0.0,
    max_value=100.0,
    value=1.0,
    step=0.1,
    help="Mức AQL công ty đang áp dụng cho loại lỗi này"
)

confidence_level = st.sidebar.selectbox(
    "Mức độ tin cậy (%)",
    options=[90, 95, 99],
    index=1,
    help="95% là mức khuyến nghị cho FMCG"
)

lot_size = st.sidebar.number_input(
    "Kích thước lô sản xuất",
    min_value=100,
    value=10000,
    step=100,
    help="Số lượng sản phẩm trong mỗi lô"
)

# Advanced settings
with st.sidebar.expander("⚙️ Cài Đặt Nâng Cao"):
    risk_assessment_method = st.selectbox(
        "Phương pháp đánh giá rủi ro",
        ["Tự động (dựa trên tỷ lệ lỗi)", "Thủ công", "FMEA Score"]
    )
    
    if risk_assessment_method == "Thủ công":
        manual_multiplier = st.slider("Hệ số nhân thủ công", 1.0, 10.0, 3.0, 0.5)
    elif risk_assessment_method == "FMEA Score":
        severity = st.slider("Mức độ nghiêm trọng (1-10)", 1, 10, 5)
        occurrence = st.slider("Tần suất xảy ra (1-10)", 1, 10, 5)
        detection = st.slider("Khả năng phát hiện (1-10)", 1, 10, 5)

# Calculations
def calculate_sample_size(defect_rate, aql, confidence, lot_size):
    """Calculate backward sampling parameters"""
    
    # Convert percentages to decimals
    p_defect = defect_rate / 100
    p_aql = aql / 100
    conf = confidence / 100
    
    # Zero-defect sample size calculation
    # n = ln(1-CL) / ln(1-p)
    n_zero_defect = math.ceil(-math.log(1 - conf) / math.log(1 - p_aql))
    
    # Determine risk level and multiplier
    ratio = defect_rate / aql if aql > 0 else float('inf')
    
    if risk_assessment_method == "Tự động (dựa trên tỷ lệ lỗi)":
        if ratio <= 1:
            risk_level = "Thấp"
            multiplier = 2
            recommended_batches = 2
            color = "green"
        elif ratio <= 3:
            risk_level = "Trung bình"
            multiplier = 3
            recommended_batches = 3
            color = "yellow"
        elif ratio <= 5:
            risk_level = "Cao"
            multiplier = 5
            recommended_batches = 5
            color = "orange"
        else:
            risk_level = "Rất cao"
            multiplier = 10
            recommended_batches = 10
            color = "red"
    elif risk_assessment_method == "Thủ công":
        multiplier = manual_multiplier
        risk_level = "Tùy chỉnh"
        recommended_batches = int(multiplier)
        color = "blue"
    else:  # FMEA
        rpn = severity * occurrence * detection
        if rpn <= 50:
            risk_level = f"RPN={rpn} (Thấp)"
            multiplier = 2
            recommended_batches = 2
            color = "green"
        elif rpn <= 100:
            risk_level = f"RPN={rpn} (Trung bình)"
            multiplier = 3
            recommended_batches = 3
            color = "yellow"
        elif rpn <= 200:
            risk_level = f"RPN={rpn} (Cao)"
            multiplier = 5
            recommended_batches = 5
            color = "orange"
        else:
            risk_level = f"RPN={rpn} (Rất cao)"
            multiplier = 10
            recommended_batches = 10
            color = "red"
    
    # Calculate backward sample size
    backward_sample_size = math.ceil(n_zero_defect * multiplier)
    
    # Ensure sample size doesn't exceed lot size
    if backward_sample_size > lot_size:
        backward_sample_size = lot_size
    
    # Calculate acceptance probability
    acceptance_probability = (1 - p_aql) ** backward_sample_size * 100
    
    # Calculate beta risk (consumer's risk)
    beta_risk = stats.binom.cdf(0, backward_sample_size, p_defect) * 100
    
    # Statistical justification for multiplier
    # Based on reducing confidence interval width
    ci_reduction = (1 - 1/math.sqrt(multiplier)) * 100
    
    return {
        'base_sample_size': n_zero_defect,
        'multiplier': multiplier,
        'backward_sample_size': backward_sample_size,
        'risk_level': risk_level,
        'recommended_batches': recommended_batches,
        'acceptance_probability': acceptance_probability,
        'beta_risk': beta_risk,
        'ratio': ratio,
        'color': color,
        'ci_reduction': ci_reduction
    }

# Calculate results
results = calculate_sample_size(actual_defect_rate, aql_level, confidence_level, lot_size)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Kết Quả Tính Toán")
    
    # Key metrics
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric(
            "Mức Rủi Ro",
            results['risk_level'],
            delta=f"Tỷ lệ: {results['ratio']:.1f}x AQL"
        )
    
    with metric_col2:
        st.metric(
            "Hệ Số Nhân",
            f"{results['multiplier']}x",
            delta=f"CI giảm {results['ci_reduction']:.0f}%"
        )
    
    with metric_col3:
        st.metric(
            "Số Mẫu/Lô",
            f"{results['backward_sample_size']}",
            delta=f"Cơ bản: {results['base_sample_size']}"
        )
    
    with metric_col4:
        st.metric(
            "Số Lô Yêu Cầu",
            f"{results['recommended_batches']} lô",
            delta=f"Tổng: {results['backward_sample_size'] * results['recommended_batches']} mẫu"
        )
    
    # OC Curve
    st.subheader("📈 Đường Cong OC (Operating Characteristic)")
    
    # Generate OC curve data
    p_values = np.linspace(0, min(0.1, actual_defect_rate/100 * 2), 100)
    pa_values = [(1 - p) ** results['backward_sample_size'] for p in p_values]
    
    fig_oc = go.Figure()
    fig_oc.add_trace(go.Scatter(
        x=p_values * 100,
        y=[pa * 100 for pa in pa_values],
        mode='lines',
        name='OC Curve',
        line=dict(color='blue', width=2)
    ))
    
    # Add markers for AQL and actual defect rate
    fig_oc.add_trace(go.Scatter(
        x=[aql_level],
        y=[results['acceptance_probability']],
        mode='markers',
        name='AQL',
        marker=dict(color='green', size=10)
    ))
    
    fig_oc.add_trace(go.Scatter(
        x=[actual_defect_rate],
        y=[results['beta_risk']],
        mode='markers',
        name='Tỷ lệ lỗi thực tế',
        marker=dict(color='red', size=10)
    ))
    
    fig_oc.update_layout(
        title="Xác suất chấp nhận lô theo tỷ lệ lỗi thực",
        xaxis_title="Tỷ lệ lỗi thực (%)",
        yaxis_title="Xác suất chấp nhận (%)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_oc, use_container_width=True)

with col2:
    st.header("📋 Hướng Dẫn Thực Hiện")
    
    # Create action plan
    st.info(f"""
    **Kế hoạch kiểm tra:**
    1. Kiểm tra **{results['backward_sample_size']} mẫu** từ mỗi lô
    2. Thực hiện trên **{results['recommended_batches']} lô liên tiếp**
    3. Tổng cộng: **{results['backward_sample_size'] * results['recommended_batches']} mẫu**
    4. Điều kiện: **0 lỗi** trong toàn bộ mẫu
    """)
    
    # Risk assessment
    if results['color'] == 'green':
        st.success("✅ Rủi ro thấp - Có thể áp dụng kiểm tra thông thường")
    elif results['color'] == 'yellow':
        st.warning("⚠️ Rủi ro trung bình - Cần giám sát chặt chẽ")
    elif results['color'] == 'orange':
        st.warning("⚠️ Rủi ro cao - Yêu cầu hành động khắc phục")
    else:
        st.error("🚨 Rủi ro rất cao - Cần dừng sản xuất và điều tra")

# Statistical justification section
with st.expander("🔬 Cơ Sở Khoa Học Cho Hệ Số Nhân"):
    st.markdown(f"""
    ### Lý do thống kê cho hệ số nhân {results['multiplier']}x:
    
    1. **Giảm độ rộng khoảng tin cậy**: 
       - Với cỡ mẫu n → {results['multiplier']}n
       - Độ rộng CI giảm: {results['ci_reduction']:.1f}%
       - Công thức: CI width ∝ 1/√n
    
    2. **Tăng Power của test (1-β)**:
       - Power = khả năng phát hiện lỗi thực sự
       - Với n={results['base_sample_size']}: Power ≈ {(1-stats.binom.cdf(0, results['base_sample_size'], actual_defect_rate/100))*100:.1f}%
       - Với n={results['backward_sample_size']}: Power ≈ {(1-results['beta_risk']/100)*100:.1f}%
    
    3. **Nguyên tắc Switching Rules (ISO 2859)**:
       - Normal → Tightened: khi 2/5 lô bị reject
       - Tightened sampling = 1.5-2x normal sampling
       - Backward sampling cần nghiêm ngặt hơn → {results['multiplier']}x
    
    4. **Cân bằng Risk**:
       - Producer's risk (α): {100-results['acceptance_probability']:.1f}% tại AQL
       - Consumer's risk (β): {results['beta_risk']:.1f}% tại tỷ lệ lỗi thực tế
    """)

# Recommendations
st.header("💡 Khuyến Nghị Cải Tiến")

col_rec1, col_rec2 = st.columns(2)

with col_rec1:
    st.subheader("Hành động ngay lập tức:")
    st.markdown("""
    - 🔍 Phân tích 5 Why cho nguyên nhân gốc
    - 🛠️ Kiểm tra và hiệu chuẩn thiết bị
    - 👥 Đào tạo lại nhân viên vận hành
    - 📊 Tăng tần suất kiểm tra in-process
    """)

with col_rec2:
    st.subheader("Cải tiến dài hạn:")
    st.markdown("""
    - 📈 Triển khai SPC cho critical parameters
    - 🎯 Đánh giá lại tiêu chuẩn AQL
    - 🔄 Cải tiến quy trình (DMAIC/Kaizen)
    - 📱 Số hóa hệ thống ghi nhận dữ liệu
    """)

# Export results
st.header("📥 Xuất Báo Cáo")

report_data = {
    'Thông số': ['Tỷ lệ lỗi thực tế (%)', 'AQL (%)', 'Độ tin cậy (%)', 
                 'Mức rủi ro', 'Hệ số nhân', 'Số mẫu/lô', 
                 'Số lô yêu cầu', 'Tổng mẫu cần kiểm'],
    'Giá trị': [actual_defect_rate, aql_level, confidence_level,
                results['risk_level'], results['multiplier'], 
                results['backward_sample_size'], results['recommended_batches'],
                results['backward_sample_size'] * results['recommended_batches']]
}

df_report = pd.DataFrame(report_data)

csv = df_report.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label="📊 Tải xuống báo cáo CSV",
    data=csv,
    file_name=f"backward_sampling_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Phát triển bởi QA Team | Dựa trên ISO 2859-1:2020 & Statistical Theory</p>
</div>
""", unsafe_allow_html=True)
