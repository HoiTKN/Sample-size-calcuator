import streamlit as st
import pandas as pd
import numpy as np
import math

# Set page config
st.set_page_config(
    page_title="Ứng Dụng QA Kiểm Tra Lùi Theo ISO-AQL",
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

# ISO 2859-1 sampling tables (simplified version)
# Dictionary format: {lot_size_code: {AQL: sample_size, ...}, ...}
iso_sampling_table = {
    'A': {0.065: 2, 0.1: 2, 0.15: 2, 0.25: 2, 0.4: 2, 0.65: 2, 1.0: 2, 1.5: 2, 2.5: 2, 4.0: 2, 6.5: 2},
    'B': {0.065: 3, 0.1: 3, 0.15: 3, 0.25: 3, 0.4: 3, 0.65: 3, 1.0: 3, 1.5: 3, 2.5: 3, 4.0: 3, 6.5: 3},
    'C': {0.065: 5, 0.1: 5, 0.15: 5, 0.25: 5, 0.4: 5, 0.65: 5, 1.0: 5, 1.5: 5, 2.5: 5, 4.0: 5, 6.5: 5},
    'D': {0.065: 8, 0.1: 8, 0.15: 8, 0.25: 8, 0.4: 8, 0.65: 8, 1.0: 8, 1.5: 8, 2.5: 8, 4.0: 8, 6.5: 8},
    'E': {0.065: 13, 0.1: 13, 0.15: 13, 0.25: 13, 0.4: 13, 0.65: 13, 1.0: 13, 1.5: 13, 2.5: 13, 4.0: 13, 6.5: 13},
    'F': {0.065: 20, 0.1: 20, 0.15: 20, 0.25: 20, 0.4: 20, 0.65: 20, 1.0: 20, 1.5: 20, 2.5: 20, 4.0: 20, 6.5: 20},
    'G': {0.065: 32, 0.1: 32, 0.15: 32, 0.25: 32, 0.4: 32, 0.65: 32, 1.0: 32, 1.5: 32, 2.5: 32, 4.0: 32, 6.5: 32},
    'H': {0.065: 50, 0.1: 50, 0.15: 50, 0.25: 50, 0.4: 50, 0.65: 50, 1.0: 50, 1.5: 50, 2.5: 50, 4.0: 50, 6.5: 50},
    'J': {0.065: 80, 0.1: 80, 0.15: 80, 0.25: 80, 0.4: 80, 0.65: 80, 1.0: 80, 1.5: 80, 2.5: 80, 4.0: 80, 6.5: 80},
    'K': {0.065: 125, 0.1: 125, 0.15: 125, 0.25: 125, 0.4: 125, 0.65: 125, 1.0: 125, 1.5: 125, 2.5: 125, 4.0: 125, 6.5: 125},
    'L': {0.065: 200, 0.1: 200, 0.15: 200, 0.25: 200, 0.4: 200, 0.65: 200, 1.0: 200, 1.5: 200, 2.5: 200, 4.0: 200, 6.5: 200},
}

# Acceptance criteria for AQLs (simplified)
acceptance_criteria = {
    0.065: 0, 0.1: 0, 0.15: 0, 0.25: 0, 
    0.4: 0, 0.65: 1, 1.0: 1, 1.5: 2, 
    2.5: 3, 4.0: 5, 6.5: 7
}

# Lot size to code mapping for General Inspection Level II
lot_size_to_code = {
    (2, 8): 'A',
    (9, 15): 'B',
    (16, 25): 'C',
    (26, 50): 'D',
    (51, 90): 'E',
    (91, 150): 'F',
    (151, 280): 'G',
    (281, 500): 'H',
    (501, 1200): 'J',
    (1201, 3200): 'K',
    (3201, 10000): 'L',
    (10001, 35000): 'M',
    (35001, 150000): 'N',
    (150001, 500000): 'P',
    (500001, float('inf')): 'Q'
}

def get_code_for_lot_size(lot_size):
    for size_range, code in lot_size_to_code.items():
        if size_range[0] <= lot_size <= size_range[1]:
            return code
    return 'Q'  # Default to largest code if lot size exceeds all ranges

def get_sample_size(lot_size, aql):
    code = get_code_for_lot_size(lot_size)
    if code in iso_sampling_table:
        if code in ['M', 'N', 'P', 'Q']:  # These codes aren't in our simplified table
            code = 'L'  # Use the largest code we have
        if aql in iso_sampling_table[code]:
            return iso_sampling_table[code][aql]
    return 200  # Default sample size if not found

def get_acceptance_number(aql):
    return acceptance_criteria.get(aql, 0)

# App title and description
st.markdown("""
<div class="header-box">
    <h1>Ứng Dụng QA Kiểm Tra Lùi Theo ISO-AQL</h1>
    <p>Công cụ hỗ trợ kiểm tra lùi khi phát hiện lỗi sản phẩm, theo tiêu chuẩn ISO 2859-1</p>
</div>
""", unsafe_allow_html=True)

# Sidebar inputs
with st.sidebar:
    st.header("Thông Số Đầu Vào")
    
    production_rate = st.number_input(
        "Tốc độ sản xuất (đơn vị/giờ)",
        min_value=10,
        max_value=10000,
        value=500,
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
        "Mức AQL (%)",
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

# Calculate intervals and sample sizes
total_minutes = 120  # 2 hours
interval_minutes = total_minutes / inspection_intervals
products_per_interval = math.ceil(production_rate * (interval_minutes / 60))
total_products = products_per_interval * inspection_intervals

# Create intervals data
intervals_data = []
for i in range(inspection_intervals):
    start_time = i * interval_minutes
    end_time = (i + 1) * interval_minutes
    
    # Get proper AQL for each interval based on proximity to defect detection
    interval_aql = aql
    if i > 0:  # For intervals further from detection point, slightly increase AQL
        if defect_type == "Lỗi nghiêm trọng (Critical)":
            interval_aql = min(aql * (1 + i * 0.2), 0.25)
        elif defect_type == "Lỗi chính (Major)":
            interval_aql = min(aql * (1 + i * 0.2), 1.5)
        else:  # Minor
            interval_aql = min(aql * (1 + i * 0.2), 6.5)
    
    # Find closest supported AQL
    closest_aql = min(aql_options, key=lambda x: abs(x - interval_aql))
    
    # Get sample size
    sample_size = get_sample_size(products_per_interval, closest_aql)
    acceptance_number = get_acceptance_number(closest_aql)
    
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
        "aql": f"{closest_aql}%",
        "sample_size": sample_size,
        "acceptance_number": acceptance_number,
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

# Additional information
st.markdown("---")
with st.expander("Thông Tin Thêm Về Phương Pháp ISO 2859-1"):
    st.markdown("""
    ### Phương Pháp Lấy Mẫu ISO 2859-1
    
    ISO 2859-1 là tiêu chuẩn quốc tế cho quy trình lấy mẫu để kiểm tra theo thuộc tính. Tiêu chuẩn này cung cấp các kế hoạch lấy mẫu được thiết kế để đảm bảo rằng lô sản phẩm đáp ứng yêu cầu về Mức Chất Lượng Chấp Nhận (AQL).
    
    #### Các Khái Niệm Chính:
    
    1. **AQL (Acceptable Quality Level)**: Mức chất lượng chấp nhận được, biểu thị bằng tỷ lệ phần trăm hoặc số lỗi trên 100 đơn vị.
    
    2. **Mức Kiểm Tra**: Xác định kích thước mẫu tương đối so với kích thước lô.
       - Mức I: Kiểm tra giảm (cỡ mẫu nhỏ hơn)
       - Mức II: Mức tiêu chuẩn (thông thường sử dụng)
       - Mức III: Kiểm tra tăng cường (cỡ mẫu lớn hơn)
    
    3. **Kích Thước Mẫu**: Được xác định dựa trên kích thước lô và mức kiểm tra.
    
    4. **Số Chấp Nhận (Ac)**: Số lỗi tối đa cho phép trong mẫu.
    
    5. **Số Từ Chối (Re)**: Số lỗi tối thiểu dẫn đến việc từ chối lô.
    
    #### Lợi Ích Của Phương Pháp:
    
    - Tiết kiệm chi phí kiểm tra
    - Dựa trên nền tảng thống kê vững chắc
    - Được công nhận rộng rãi trong ngành công nghiệp
    - Cho phép điều chỉnh mức độ kiểm tra dựa trên lịch sử chất lượng
    
    #### Quy Trình Kiểm Tra Tuần Tự:
    
    Quy trình kiểm tra tuần tự được đề xuất trong ứng dụng này là một cải tiến của phương pháp ISO 2859-1 truyền thống:
    
    1. Bắt đầu với khoảng thời gian gần nhất với thời điểm phát hiện lỗi
    2. Áp dụng tiêu chí chấp nhận/từ chối cho từng khoảng
    3. Chỉ tiến hành kiểm tra các khoảng tiếp theo nếu cần thiết
    4. Giải phóng các lô đạt yêu cầu để tối ưu hóa quy trình
    """)

st.markdown("---")
st.caption("Ứng dụng QA Kiểm Tra Lùi Theo ISO-AQL | Dựa trên tiêu chuẩn ISO 2859-1")

# Add download button for the inspection plan
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Tải xuống kế hoạch kiểm tra (CSV)",
    data=csv,
    file_name="ke_hoach_kiem_tra.csv",
    mime="text/csv",
)
