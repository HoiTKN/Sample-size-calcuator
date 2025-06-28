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
- Phân tích Pattern lỗi thực tế
""")

# Sidebar for inputs
st.sidebar.header("📝 Thông Số Đầu Vào")

# Defect Pattern Analysis
st.sidebar.subheader("🔍 Phân Tích Pattern Lỗi")
defect_pattern = st.sidebar.selectbox(
    "Pattern lỗi phát hiện",
    ["Chọn pattern...", 
     "A - Tập trung (1 thùng nhiều lỗi)", 
     "B - Gián đoạn (vài thùng ít lỗi)",
     "C - Rời rạc (nhiều thùng ít lỗi)"],
    help="Pattern lỗi ảnh hưởng đến chiến lược kiểm lùi"
)

# Input parameters
total_defects = st.sidebar.number_input(
    "Tổng số lỗi phát hiện",
    min_value=1,
    value=5,
    step=1,
    help="Tổng số gói lỗi trong lần kiểm"
)

sample_size_checked = st.sidebar.number_input(
    "Tổng số mẫu đã kiểm (gói)",
    min_value=1,
    value=150,
    step=1,
    help="Tổng số gói đã kiểm tra"
)

# Calculate actual defect rate
actual_defect_rate = (total_defects / sample_size_checked) * 100

st.sidebar.info(f"Tỷ lệ lỗi thực tế: {actual_defect_rate:.2f}%")

aql_level = st.sidebar.number_input(
    "AQL - Mức chất lượng chấp nhận (%)",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=0.1,
    help="AQL cho lỗi rách thường là 0%"
)

confidence_level = st.sidebar.selectbox(
    "Mức độ tin cậy (%)",
    options=[90, 95, 99],
    index=1,
    help="95% là mức khuyến nghị cho FMCG"
)

# Production parameters
st.sidebar.subheader("📦 Thông Số Sản Xuất")
boxes_per_hour = st.sidebar.number_input(
    "Số thùng sản xuất/giờ",
    min_value=100,
    value=5000,
    step=100,
    help="Tốc độ sản xuất"
)

units_per_box = st.sidebar.number_input(
    "Số gói/thùng",
    min_value=1,
    value=30,
    step=1
)

hold_duration = st.sidebar.number_input(
    "Thời gian hold (giờ)",
    min_value=1.0,
    value=2.0,
    step=0.5,
    help="Thường là 2h từ lần kiểm OK gần nhất"
)

# Advanced settings
risk_assessment_method = "Pattern-based"
manual_multiplier = 3.0
severity = occurrence = detection = 5

with st.sidebar.expander("⚙️ Cài Đặt Nâng Cao"):
    risk_assessment_method = st.selectbox(
        "Phương pháp đánh giá rủi ro",
        ["Pattern-based", "Tự động (tỷ lệ lỗi)", "Thủ công", "FMEA Score"]
    )
    
    if risk_assessment_method == "Thủ công":
        manual_multiplier = st.slider("Hệ số nhân thủ công", 1.0, 10.0, 3.0, 0.5)
    elif risk_assessment_method == "FMEA Score":
        severity = st.slider("Mức độ nghiêm trọng (1-10)", 1, 10, 5)
        occurrence = st.slider("Tần suất xảy ra (1-10)", 1, 10, 5)
        detection = st.slider("Khả năng phát hiện (1-10)", 1, 10, 5)

# Calculations
def calculate_backward_sampling(defect_rate, aql, confidence, pattern, risk_method):
    """Calculate backward sampling based on pattern analysis"""
    
    # Convert percentages to decimals
    p_defect = defect_rate / 100
    p_aql = (aql / 100) if aql > 0 else 0.001  # Avoid log(0)
    conf = confidence / 100
    
    # Zero-defect sample size calculation
    n_zero_defect = math.ceil(-math.log(1 - conf) / math.log(1 - p_aql))
    
    # Pattern-based approach
    if risk_method == "Pattern-based" and pattern != "Chọn pattern...":
        if "A -" in pattern:  # Clustered
            boxes_to_check = 200
            risk_level = "Tập trung - Rủi ro thấp"
            multiplier = 2
            strategy = "Kiểm 4-8h ngược từ thời điểm lỗi"
            color = "green"
        elif "B -" in pattern:  # Intermittent
            boxes_to_check = 500
            risk_level = "Gián đoạn - Rủi ro trung bình"
            multiplier = 3
            strategy = "Kiểm 8-12h ngược, monitor trend"
            color = "yellow"
        elif "C -" in pattern:  # Random
            boxes_to_check = 1000
            risk_level = "Rời rạc - Rủi ro cao (hệ thống)"
            multiplier = 5
            strategy = "Kiểm 12-24h ngược, root cause analysis"
            color = "red"
        else:
            boxes_to_check = 500
            risk_level = "Không xác định"
            multiplier = 3
            strategy = "Áp dụng mức trung bình"
            color = "gray"
    else:
        # Fallback to ratio-based
        ratio = defect_rate / aql if aql > 0 else float('inf')
        
        if risk_method == "Tự động (tỷ lệ lỗi)":
            if ratio <= 1:
                risk_level = "Thấp"
                multiplier = 2
                boxes_to_check = 200
                color = "green"
            elif ratio <= 3:
                risk_level = "Trung bình"
                multiplier = 3
                boxes_to_check = 500
                color = "yellow"
            elif ratio <= 5:
                risk_level = "Cao"
                multiplier = 5
                boxes_to_check = 800
                color = "orange"
            else:
                risk_level = "Rất cao"
                multiplier = 10
                boxes_to_check = 1000
                color = "red"
        elif risk_method == "Thủ công":
            multiplier = manual_multiplier
            boxes_to_check = int(200 * multiplier / 2)
            risk_level = "Tùy chỉnh"
            color = "blue"
        else:  # FMEA
            rpn = severity * occurrence * detection
            if rpn <= 50:
                risk_level = f"RPN={rpn} (Thấp)"
                multiplier = 2
                boxes_to_check = 200
                color = "green"
            elif rpn <= 100:
                risk_level = f"RPN={rpn} (Trung bình)"
                multiplier = 3
                boxes_to_check = 500
                color = "yellow"
            elif rpn <= 200:
                risk_level = f"RPN={rpn} (Cao)"
                multiplier = 5
                boxes_to_check = 800
                color = "orange"
            else:
                risk_level = f"RPN={rpn} (Rất cao)"
                multiplier = 10
                boxes_to_check = 1000
                color = "red"
        
        strategy = f"Kiểm {boxes_to_check} thùng liên tục"
    
    # Calculate sample size
    samples_per_box = units_per_box
    total_samples = boxes_to_check * samples_per_box
    
    # Calculate probabilities
    acceptance_probability = (1 - p_aql) ** total_samples * 100
    beta_risk = stats.binom.cdf(0, total_samples, p_defect) * 100
    
    # Time calculation
    hours_to_check_back = boxes_to_check / boxes_per_hour
    
    return {
        'boxes_to_check': boxes_to_check,
        'total_samples': total_samples,
        'risk_level': risk_level,
        'multiplier': multiplier,
        'strategy': strategy,
        'acceptance_probability': acceptance_probability,
        'beta_risk': beta_risk,
        'hours_to_check_back': hours_to_check_back,
        'color': color,
        'base_sample_size': n_zero_defect
    }

# Calculate results
results = calculate_backward_sampling(
    actual_defect_rate, 
    aql_level, 
    confidence_level, 
    defect_pattern,
    risk_assessment_method
)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Kết Quả Phân Tích")
    
    # Key metrics
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric(
            "Pattern & Rủi Ro",
            results['risk_level'].split(' - ')[0],
            delta=results['risk_level'].split(' - ')[1] if ' - ' in results['risk_level'] else ""
        )
    
    with metric_col2:
        st.metric(
            "Số Thùng Kiểm Lùi",
            f"{results['boxes_to_check']:,}",
            delta=f"{results['hours_to_check_back']:.1f}h sản xuất"
        )
    
    with metric_col3:
        st.metric(
            "Tổng Mẫu Kiểm",
            f"{results['total_samples']:,}",
            delta=f"{results['total_samples']/units_per_box:.0f} thùng"
        )
    
    with metric_col4:
        total_hold = int(boxes_per_hour * hold_duration)
        st.metric(
            "Tổng Hàng Hold",
            f"{total_hold:,} thùng",
            delta=f"{hold_duration}h sản xuất"
        )
    
    # Pattern explanation
    if defect_pattern != "Chọn pattern...":
        st.subheader("📋 Phân Tích Pattern")
        
        pattern_info = {
            "A -": {
                "desc": "Lỗi tập trung trong 1 hoặc vài thùng",
                "cause": "Sự cố thiết bị tức thời, nguyên liệu lỗi cục bộ",
                "action": "Focus kiểm tra ±30 phút quanh thời điểm lỗi"
            },
            "B -": {
                "desc": "Lỗi xuất hiện gián đoạn, không đều",
                "cause": "Dao động quy trình, thiết bị không ổn định",
                "action": "Kiểm tra đều theo thời gian, theo dõi trend"
            },
            "C -": {
                "desc": "Lỗi phân bố ngẫu nhiên trên nhiều thùng",
                "cause": "Vấn đề hệ thống, quy trình không ổn định",
                "action": "Random sampling toàn bộ, phân tích root cause"
            }
        }
        
        for key, info in pattern_info.items():
            if key in defect_pattern:
                st.info(f"""
                **Đặc điểm**: {info['desc']}
                
                **Nguyên nhân thường gặp**: {info['cause']}
                
                **Chiến lược kiểm tra**: {info['action']}
                """)
                break
    
    # Visualization
    st.subheader("📈 Phân Bổ Kiểm Tra Theo Thời Gian")
    
    # Create timeline visualization
    hours_back = np.arange(0, -24, -1)
    check_intensity = np.zeros_like(hours_back, dtype=float)
    
    if "A -" in defect_pattern:
        # Concentrated around defect time
        check_intensity[0:4] = 100
        check_intensity[4:8] = 50
    elif "B -" in defect_pattern:
        # Even distribution
        check_intensity[0:12] = 80
    elif "C -" in defect_pattern:
        # Wide distribution
        check_intensity[0:24] = 60
    else:
        check_intensity[0:int(results['hours_to_check_back'])] = 70
    
    fig_timeline = go.Figure()
    fig_timeline.add_trace(go.Bar(
        x=hours_back,
        y=check_intensity,
        name='Mật độ kiểm tra (%)',
        marker_color=results['color']
    ))
    
    fig_timeline.update_layout(
        title="Phân bố mật độ kiểm tra theo thời gian",
        xaxis_title="Giờ (từ thời điểm phát hiện lỗi)",
        yaxis_title="Mật độ kiểm tra (%)",
        showlegend=False
    )
    
    st.plotly_chart(fig_timeline, use_container_width=True)

with col2:
    st.header("🎯 Kế Hoạch Hành Động")
    
    # Action plan
    st.success(f"**Chiến lược**: {results['strategy']}")
    
    # Step by step guide
    st.subheader("📝 Các bước thực hiện")
    
    steps = [
        f"1. **Hold** {int(boxes_per_hour * hold_duration):,} thùng ({hold_duration}h sản xuất)",
        f"2. **Lấy mẫu** random 10-20 thùng để confirm pattern",
        f"3. **Kiểm lùi** {results['boxes_to_check']:,} thùng",
        f"4. **Điều kiện**: 0 lỗi trong {results['total_samples']:,} mẫu",
        f"5. **Release** theo batch nếu đạt"
    ]
    
    for step in steps:
        st.markdown(step)
    
    # Risk assessment
    if results['color'] == 'green':
        st.success("✅ Rủi ro thấp - Có thể release phần xa thời điểm lỗi")
    elif results['color'] == 'yellow':
        st.warning("⚠️ Rủi ro trung bình - Release theo batch, monitor tiếp")
    elif results['color'] == 'orange':
        st.warning("⚠️ Rủi ro cao - Cần xác định root cause")
    else:
        st.error("🚨 Rủi ro rất cao - Hold thêm, phân tích hệ thống")

# Release Strategy
st.header("📦 Chiến Lược Release")

col_rel1, col_rel2 = st.columns(2)

with col_rel1:
    st.subheader("Thứ tự ưu tiên release:")
    
    release_priority = pd.DataFrame({
        'Thứ tự': [1, 2, 3, 4],
        'Khoảng thời gian': [
            f'{int(results["hours_to_check_back"])}-{int(hold_duration)}h trước',
            f'{int(results["hours_to_check_back"]/2)}-{int(results["hours_to_check_back"])}h trước',
            f'2-{int(results["hours_to_check_back"]/2)}h trước',
            '0-2h gần nhất'
        ],
        'Điều kiện': [
            f'{int(results["boxes_to_check"]/4)} thùng OK',
            f'{int(results["boxes_to_check"]/2)} thùng OK',
            f'{int(results["boxes_to_check"]*3/4)} thùng OK',
            f'{results["boxes_to_check"]} thùng OK'
        ]
    })
    
    st.dataframe(release_priority, hide_index=True)

with col_rel2:
    st.subheader("Quyết định theo Pattern:")
    
    decision_matrix = {
        "Pattern A": "Release phần xa thời điểm lỗi trước",
        "Pattern B": "Release theo batch nhỏ, monitor",
        "Pattern C": "Chờ root cause, release thận trọng"
    }
    
    for pattern, decision in decision_matrix.items():
        if pattern[0] in str(defect_pattern):
            st.info(f"**{pattern}**: {decision}")

# Statistical justification
with st.expander("🔬 Cơ Sở Thống Kê"):
    st.markdown(f"""
    ### Tính toán dựa trên:
    
    1. **Độ tin cậy {confidence_level}%**:
       - Cần {results['base_sample_size']} mẫu zero-defect cơ bản
       - Pattern factor: ×{results['multiplier']}
       - Tổng: {results['total_samples']:,} mẫu
    
    2. **Xác suất chấp nhận**:
       - Tại AQL: {results['acceptance_probability']:.2f}%
       - Beta risk: {results['beta_risk']:.2f}%
    
    3. **Logic Pattern-based**:
       - Lỗi tập trung → Vấn đề cục bộ → Ít mẫu
       - Lỗi rời rạc → Vấn đề hệ thống → Nhiều mẫu
       - Cân bằng risk vs efficiency
    """)

# Recommendations
st.header("💡 Khuyến Nghị")

col_rec1, col_rec2 = st.columns(2)

with col_rec1:
    st.subheader("Hành động ngay:")
    actions = {
        "A -": [
            "🔍 Check thiết bị tại thời điểm lỗi",
            "📦 Verify nguyên liệu cùng batch",
            "👥 Phỏng vấn operator ca đó",
            "🛠️ Calibrate thiết bị liên quan"
        ],
        "B -": [
            "📊 Phân tích trend 24h",
            "🔄 Check cycle time variations",
            "🌡️ Monitor environmental conditions",
            "⚙️ Review maintenance log"
        ],
        "C -": [
            "🏭 Stop & investigate system",
            "📋 Full process audit",
            "🔬 Lab test samples",
            "👨‍🏫 Retrain all operators"
        ]
    }
    
    for key, items in actions.items():
        if key in str(defect_pattern):
            for item in items:
                st.markdown(item)
            break

with col_rec2:
    st.subheader("Cải tiến dài hạn:")
    st.markdown("""
    - 📈 Triển khai SPC real-time
    - 🎯 Review & update AQL
    - 🔄 Standardize process (SOP)
    - 📱 Digital tracking system
    - 🤖 Auto defect detection
    """)

# Export results
st.header("📥 Xuất Báo Cáo")

# Prepare comprehensive report
report_data = {
    'Thông số': [
        'Pattern lỗi',
        'Tổng lỗi phát hiện',
        'Tổng mẫu đã kiểm',
        'Tỷ lệ lỗi thực tế (%)',
        'AQL (%)',
        'Độ tin cậy (%)',
        'Mức rủi ro',
        'Số thùng kiểm lùi',
        'Tổng mẫu cần kiểm',
        'Thời gian kiểm lùi (h)',
        'Chiến lược'
    ],
    'Giá trị': [
        defect_pattern,
        total_defects,
        sample_size_checked,
        f"{actual_defect_rate:.2f}",
        aql_level,
        confidence_level,
        results['risk_level'],
        results['boxes_to_check'],
        results['total_samples'],
        f"{results['hours_to_check_back']:.1f}",
        results['strategy']
    ]
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
    <p>Phát triển bởi QA Team | Pattern-based Backward Sampling v2.0</p>
</div>
""", unsafe_allow_html=True)
