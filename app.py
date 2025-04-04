import streamlit as st
import pandas as pd
import numpy as np
import math

# Set page config
st.set_page_config(
    page_title="Ứng Dụng QA Kiểm Tra Lùi Theo Phân Tầng Rủi Ro",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS
st.markdown("""
<style>
.main {
    padding: 2rem;
}
.result-box {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
}
.green-box {
    background-color: #d5f5e3;
}
.yellow-box {
    background-color: #fdebd0;
}
.red-box {
    background-color: #f5b7b1;
}
.time-interval {
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #ddd;
}
.header-box {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    border-left: 5px solid #4e73df;
}
</style>
""", unsafe_allow_html=True)

# App title and description
st.markdown("""
<div class="header-box">
    <h1>Ứng Dụng QA Kiểm Tra Lùi Theo Phân Tầng Rủi Ro</h1>
    <p>Công cụ hỗ trợ kiểm tra lùi khi phát hiện lỗi sản phẩm, với phân bổ mẫu theo mức độ rủi ro</p>
</div>
""", unsafe_allow_html=True)

# Sidebar inputs
with st.sidebar:
    st.header("Thông Số Đầu Vào")
    
    production_rate = st.number_input(
        "Tốc độ sản xuất (đơn vị/giờ)",
        min_value=10,
        max_value=10000,
        value=924,
        step=10
    )
    
    defect_type = st.selectbox(
        "Phân loại lỗi",
        options=["Lỗi nghiêm trọng (Critical)", "Lỗi chính (Major)", "Lỗi phụ (Minor)"]
    )
    
    # Set AQL based on defect type
    if defect_type == "Lỗi nghiêm trọng (Critical)":
        aql_options = [0.065, 0.1, 0.15, 0.25]
        default_aql_index = 1  # 0.1%
    elif defect_type == "Lỗi chính (Major)":
        aql_options = [0.4, 0.65, 1.0, 1.5]
        default_aql_index = 2  # 1.0%
    else:  # Minor
        aql_options = [1.5, 2.5, 4.0, 6.5]
        default_aql_index = 1  # 2.5%
    
    aql = st.selectbox(
        "Mức AQL cơ sở (%)",
        options=aql_options,
        index=default_aql_index,
        format_func=lambda x: f"{x}%"
    )
    
    inspection_level = st.selectbox(
        "Mức độ kiểm tra",
        options=["Tiêu chuẩn", "Tăng cường", "Giảm"],
        index=0
    )
    
    inspection_intervals = st.number_input(
        "Số lượng khoảng thời gian kiểm tra",
        min_value=2,
        max_value=8,
        value=4,
        step=1,
        help="Chia 2h thành bao nhiêu khoảng thời gian để kiểm tra"
    )
    
    total_samples = st.number_input(
        "Tổng số mẫu có thể kiểm tra",
        min_value=50,
        max_value=1000,
        value=200,
        step=10,
        help="Tổng số mẫu tối đa có thể kiểm tra cho tất cả các khoảng thời gian"
    )

# Risk-based distribution model
def calculate_risk_distribution(intervals, total_samples, defect_type):
    """
    Calculate risk-based sample distribution across intervals
    """
    # Calculate risk weights based on proximity to detection point
    if defect_type == "Lỗi nghiêm trọng (Critical)":
        # Exponential risk distribution for critical defects
        weights = [math.exp(-0.8 * i) for i in range(intervals)]
    elif defect_type == "Lỗi chính (Major)":
        # Less steep exponential for major defects
        weights = [math.exp(-0.6 * i) for i in range(intervals)]
    else:  # Minor
        # Closer to linear for minor defects
        weights = [math.exp(-0.4 * i) for i in range(intervals)]
    
    # Normalize weights to sum to 1
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    
    # Calculate sample sizes based on weights
    samples = [round(total_samples * w) for w in normalized_weights]
    
    # Ensure minimum sample size (5) for each interval
    samples = [max(s, 5) for s in samples]
    
    # Adjust if the sum exceeds the total
    while sum(samples) > total_samples:
        # Find the interval with largest sample that's not at minimum
        max_idx = samples.index(max([s for s in samples if s > 5]))
        samples[max_idx] -= 1
    
    # Adjust if the sum is less than the total
    remaining = total_samples - sum(samples)
    if remaining > 0:
        # Distribute remaining samples to earlier intervals
        for i in range(min(remaining, intervals)):
            samples[i] += 1
    
    return samples

# Calculate AQL progression based on proximity to detection
def calculate_aql_progression(base_aql, intervals, defect_type):
    """
    Calculate AQL progression for intervals, with stricter AQLs for closer intervals
    """
    aqls = []
    
    if defect_type == "Lỗi nghiêm trọng (Critical)":
        # For critical defects, tighter AQL progression
        multipliers = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    elif defect_type == "Lỗi chính (Major)":
        # For major defects, moderate AQL progression
        multipliers = [1.0, 1.3, 1.6, 2.0, 2.3, 2.6, 3.0, 3.3]
    else:
        # For minor defects, more relaxed AQL progression
        multipliers = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4]
    
    # Limit multipliers array to the number of intervals
    multipliers = multipliers[:intervals]
    
    for m in multipliers:
        # Calculate AQL for this interval
        interval_aql = base_aql * m
        
        # Find closest standard AQL value
        standard_aqls = [0.065, 0.1, 0.15, 0.25, 0.4, 0.65, 1.0, 1.5, 2.5, 4.0, 6.5]
        closest_aql = min(standard_aqls, key=lambda x: abs(x - interval_aql))
        
        aqls.append(closest_aql)
    
    return aqls

# Calculate acceptance numbers
def get_acceptance_numbers(aqls):
    """
    Get acceptance numbers based on AQL values
    """
    # Simplified acceptance criteria table
    ac_table = {
        0.065: 0, 
        0.1: 0, 
        0.15: 0, 
        0.25: 0, 
        0.4: 0, 
        0.65: 1, 
        1.0: 2, 
        1.5: 3, 
        2.5: 5, 
        4.0: 7, 
        6.5: 10
    }
    
    acceptance_numbers = []
    for aql_val in aqls:
        # For critical defects with low AQL, ensure zero acceptance
        if aql_val <= 0.25:
            acceptance_numbers.append(0)
        else:
            acceptance_numbers.append(ac_table.get(aql_val, 0))
    
    return acceptance_numbers

# Calculate intervals and sample sizes
total_minutes = 120  # 2 hours
interval_minutes = total_minutes / inspection_intervals
products_per_interval = math.ceil(production_rate * (interval_minutes / 60))
total_products = products_per_interval * inspection_intervals

# Get sample distribution based on risk
sample_distribution = calculate_risk_distribution(inspection_intervals, total_samples, defect_type)

# Get AQL progression
aql_progression = calculate_aql_progression(aql, inspection_intervals, defect_type)

# Get acceptance numbers
acceptance_numbers = get_acceptance_numbers(aql_progression)

# Create intervals data
intervals_data = []
for i in range(inspection_intervals):
    start_time = i * interval_minutes
    end_time = (i + 1) * interval_minutes
    
    # Get sample size for this interval
    sample_size = sample_distribution[i]
    
    # Adjustments based on inspection level
    if inspection_level == "Tăng cường":
        sample_size = math.ceil(sample_size * 1.2)
    elif inspection_level == "Giảm":
        sample_size = math.floor(sample_size * 0.8)
        sample_size = max(sample_size, 5)  # Ensure minimum sample size
    
    # Calculate inspection percentage
    inspection_percentage = round((sample_size / products_per_interval) * 100, 1)
    
    intervals_data.append({
        "interval": f"{i+1}",
        "time_range": f"{int(start_time)}-{int(end_time)} phút",
        "products": products_per_interval,
        "aql": f"{aql_progression[i]}%",
        "sample_size": sample_size,
        "acceptance_number": acceptance_numbers[i],
        "inspection_percentage": f"{inspection_percentage}%"
    })

# Main content
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Kế Hoạch Kiểm Tra Lùi")
    
    # Display intervals table
    df = pd.DataFrame(intervals_data)
    st.dataframe(
        df,
        column_config={
            "interval": "Khoảng",
            "time_range": "Khoảng thời gian",
            "products": "Sản phẩm",
            "aql": "AQL",
            "sample_size": "Cỡ mẫu",
            "acceptance_number": "Số chấp nhận",
            "inspection_percentage": "% Kiểm tra"
        },
        hide_index=True
    )
    
    # Calculate totals
    total_sample_size = sum(interval["sample_size"] for interval in intervals_data)
    overall_inspection_percentage = round((total_sample_size / total_products) * 100, 1)
    
    st.markdown(f"""
    <div class="result-box green-box">
        <h4>Tổng Quan:</h4>
        <p>- Tổng số sản phẩm (2 giờ): <b>{total_products}</b> đơn vị</p>
        <p>- Tổng số mẫu cần kiểm tra: <b>{total_sample_size}</b> đơn vị</p>
        <p>- Tỷ lệ kiểm tra: <b>{overall_inspection_percentage}%</b></p>
        <p>- Giảm khối lượng kiểm tra: <b>{100 - overall_inspection_percentage}%</b> so với kiểm tra 100%</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.header("Quy Trình Kiểm Tra Tuần Tự")
    
    st.markdown("""
    <div class="result-box yellow-box">
        <h4>Hướng Dẫn Thực Hiện:</h4>
        <ol>
            <li>Bắt đầu kiểm tra khoảng thời gian gần nhất với thời điểm phát hiện lỗi</li>
            <li>Kiểm tra đúng số lượng mẫu theo bảng</li>
            <li>Ghi lại số lỗi phát hiện được</li>
            <li>So sánh với số chấp nhận và quyết định lô</li>
            <li>Tiếp tục kiểm tra các khoảng thời gian tiếp theo</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Acceptance criteria explanation
    st.subheader("Tiêu Chí Chấp Nhận/Từ Chối")
    
    for interval in intervals_data:
        st.markdown(f"""
        <div class="time-interval">
            <h5>Khoảng {interval['interval']} ({interval['time_range']})</h5>
            <p>- Cỡ mẫu: {interval['sample_size']} đơn vị</p>
            <p>- Số chấp nhận (Ac): {interval['acceptance_number']}</p>
            <p>- Số từ chối (Re): {interval['acceptance_number'] + 1}</p>
            <p>- <b>Quyết định:</b> Nếu số lỗi ≤ {interval['acceptance_number']}, chấp nhận lô và giải phóng. Nếu số lỗi ≥ {interval['acceptance_number'] + 1}, từ chối lô và giữ lại.</p>
        </div>
        """, unsafe_allow_html=True)

# Visualization of sample distribution
st.header("Phân Tích Trực Quan")

# Prepare data for chart
chart_data = {
    'Khoảng thời gian': [d['time_range'] for d in intervals_data],
    'Cỡ mẫu': [d['sample_size'] for d in intervals_data],
    'AQL (%)': [float(d['aql'].replace('%', '')) for d in intervals_data]
}

chart_df = pd.DataFrame(chart_data)

# Create two columns for the charts
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Phân Bổ Cỡ Mẫu Theo Khoảng Thời Gian")
    st.bar_chart(chart_df.set_index('Khoảng thời gian')['Cỡ mẫu'])
    st.caption("Phân bổ theo mức độ rủi ro: tập trung nhiều mẫu hơn vào khoảng thời gian gần điểm phát hiện lỗi")

with chart_col2:
    st.subheader("Mức AQL Theo Khoảng Thời Gian")
    st.line_chart(chart_df.set_index('Khoảng thời gian')['AQL (%)'])
    st.caption("AQL tăng dần theo khoảng cách từ điểm phát hiện lỗi: càng xa càng ít nghiêm ngặt")

# Additional information
st.markdown("---")
with st.expander("Lý Do Phân Bổ Mẫu Theo Phân Tầng Rủi Ro"):
    st.markdown("""
    ### Tại Sao Sử Dụng Phân Tầng Rủi Ro?
    
    Phương pháp phân tầng rủi ro phân bổ nhiều mẫu hơn cho các khoảng thời gian gần với điểm phát hiện lỗi. Điều này dựa trên các nguyên tắc thống kê và thực tế sản xuất:
    
    1. **Xác suất lỗi không đồng đều theo thời gian**: Lỗi trong sản xuất thường xuất hiện theo xu hướng, không phải ngẫu nhiên đều đặn.
    
    2. **Hiệu quả nguồn lực**: Tập trung nguồn lực vào các khoảng thời gian có rủi ro cao nhất.
    
    3. **Tối ưu hóa phát hiện lỗi**: Tăng khả năng phát hiện lỗi bằng cách kiểm tra kỹ lưỡng hơn ở khu vực có xác suất lỗi cao.
    
    4. **Tính lũy tích của độ tin cậy**: Nếu các khoảng thời gian gần hơn không có lỗi, khả năng cao là các khoảng xa hơn cũng sẽ không có lỗi.
    
    ### Công Thức Phân Bổ
    
    Chúng tôi sử dụng phân bổ hàm mũ để tính trọng số cho mỗi khoảng thời gian:
    
    - **Lỗi nghiêm trọng**: `w = exp(-0.8 * i)` → Giảm nhanh (tập trung mạnh vào khoảng gần nhất)
    - **Lỗi chính**: `w = exp(-0.6 * i)` → Giảm vừa phải
    - **Lỗi phụ**: `w = exp(-0.4 * i)` → Giảm chậm hơn (phân bổ đều hơn)
    
    Trong đó `i` là chỉ số khoảng thời gian (0 = gần nhất, 1 = thứ hai, v.v.)
    
    ### AQL Theo Khoảng Thời Gian
    
    AQL cũng được điều chỉnh theo khoảng cách từ điểm phát hiện lỗi:
    
    - Khoảng gần nhất: AQL thấp nhất (nghiêm ngặt nhất)
    - Khoảng xa dần: AQL tăng dần (ít nghiêm ngặt hơn)
    
    Điều này phản ánh mức độ rủi ro giảm dần theo khoảng cách.
    """)

# Add download button for the inspection plan
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Tải xuống kế hoạch kiểm tra (CSV)",
    data=csv,
    file_name="ke_hoach_kiem_tra_rui_ro.csv",
    mime="text/csv",
)

st.markdown("---")
st.caption("Ứng dụng QA Kiểm Tra Lùi Theo Phân Tầng Rủi Ro")
st.caption("Tối ưu nguồn lực QA trong khi vẫn đảm bảo chất lượng sản phẩm")
