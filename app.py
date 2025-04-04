import streamlit as st
import numpy as np
import pandas as pd
import math

# Set page config
st.set_page_config(
    page_title="QA Sample Size Calculator",
    layout="centered",
    initial_sidebar_state="collapsed",
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
</style>
""", unsafe_allow_html=True)

# App title
st.title("Công Cụ Tính Kích Thước Mẫu QA")
st.markdown("---")

# Create two columns for input
col1, col2 = st.columns(2)

with col1:
    st.subheader("Thông số đầu vào")
    
    # AQL selection
    aql_options = [0, 0.1, 1, 2.5, 4, 6.5]
    aql = st.selectbox("AQL (%)", aql_options, index=2)  # Default to 1%
    
    # Determine confidence level based on AQL
    if aql <= 1:
        confidence_level = 0.99
        confidence_text = "99%"
    elif aql <= 4:
        confidence_level = 0.95
        confidence_text = "95%"
    else:
        confidence_level = 0.90
        confidence_text = "90%"
    
    st.info(f"Mức độ tin cậy: {confidence_text} (tự động dựa trên AQL)")
    
    # Defect rate input
    defect_rate = st.number_input("Tỷ lệ lỗi thực tế (%)", 
                                 min_value=0.0, 
                                 max_value=100.0, 
                                 value=0.5,
                                 step=0.1,
                                 format="%.1f")
    
    # Total held quantity input
    held_quantity = st.number_input("Tổng số lượng đang giữ", 
                                  min_value=1, 
                                  value=5000,
                                  step=100)

# Calculate sample size
if aql > 0:  # Avoid division by zero
    # Formula: n = ln(1-CL) / ln(1-AQL)
    required_sample_size = math.ceil(math.log(1 - confidence_level) / math.log(1 - aql/100))
else:
    required_sample_size = held_quantity  # If AQL is 0, inspect 100%

# Adjust sample size if needed (when sample > 10% of population)
if required_sample_size > held_quantity * 0.1:
    adjusted_sample_size = math.ceil((required_sample_size * held_quantity) / 
                                   (required_sample_size + (held_quantity - 1)))
else:
    adjusted_sample_size = required_sample_size

# Expected defects
expected_defects = round(adjusted_sample_size * defect_rate / 100, 1)

# Display results
with col2:
    st.subheader("Kết quả")
    
    st.metric("Kích thước mẫu yêu cầu", f"{required_sample_size} đơn vị")
    st.metric("Kích thước mẫu điều chỉnh", f"{adjusted_sample_size} đơn vị")
    st.metric("Số lỗi dự kiến trong mẫu", f"{expected_defects}")
    
    # Recommendation with color coding
    if expected_defects < 1:
        box_class = "green-box"
        recommendation = f"✓ Chấp nhận lô nếu không tìm thấy lỗi trong mẫu {adjusted_sample_size} đơn vị"
    elif expected_defects < 3:
        box_class = "yellow-box"
        recommendation = f"⚠️ Xem xét kiểm tra 100%: Dự kiến tìm thấy {expected_defects} lỗi trong mẫu"
    else:
        box_class = "red-box"
        recommendation = f"⚠️ Khuyến nghị kiểm tra 100%: Dự kiến tìm thấy {expected_defects} lỗi trong mẫu"
    
    st.markdown(f"""
    <div class="result-box {box_class}">
        <h4>Khuyến nghị:</h4>
        <p>{recommendation}</p>
    </div>
    """, unsafe_allow_html=True)

# Display reference table
st.markdown("---")
st.subheader("Bảng tham khảo mức độ tin cậy")

reference_data = {
    'AQL (%)': ['≤ 1.0%', '> 1.0% và ≤ 4.0%', '> 4.0%'],
    'Mức độ tin cậy': ['99%', '95%', '90%']
}

reference_df = pd.DataFrame(reference_data)
st.table(reference_df)

# Add more information section
st.markdown("---")
with st.expander("Thông tin thêm về phương pháp lấy mẫu"):
    st.markdown("""
    ### Công thức tính kích thước mẫu

    Công thức sử dụng trong công cụ này dựa trên phương pháp lấy mẫu chấp nhận không lỗi (Zero Acceptance Number Sampling):

    **n = ln(1-CL) / ln(1-AQL)**

    Trong đó:
    - n: Kích thước mẫu yêu cầu
    - CL: Mức độ tin cậy (0.90, 0.95 hoặc 0.99)
    - AQL: Mức chất lượng chấp nhận (dạng thập phân, ví dụ: 0.01 cho 1%)

    ### Điều chỉnh cho dân số hữu hạn

    Khi kích thước mẫu vượt quá 10% tổng số lượng, chúng tôi áp dụng công thức điều chỉnh:

    **n_adjusted = (n × N) / (n + (N - 1))**

    Trong đó:
    - n_adjusted: Kích thước mẫu điều chỉnh
    - n: Kích thước mẫu ban đầu
    - N: Tổng số lượng đang giữ

    ### Cách diễn giải kết quả

    Nếu bạn kiểm tra số lượng mẫu được đề xuất và không tìm thấy lỗi nào, bạn có thể tự tin rằng tỷ lệ lỗi trong lô hàng thấp hơn giá trị AQL với mức độ tin cậy đã chọn.
    """)

# Add footer
st.caption("Công thức: n = ln(1-CL) / ln(1-AQL)")
st.caption("Dựa trên phương pháp lấy mẫu chấp nhận không lỗi")
st.caption("Liên hệ QA Manager để biết thêm thông tin")

# Add download example data button
if st.button("Tải xuống thông tin phương pháp lấy mẫu"):
    csv = """AQL,Confidence Level,Sample Size
0.1%,99%,4605
0.1%,95%,2995
1.0%,99%,459
1.0%,95%,299
2.5%,95%,119
2.5%,90%,92
4.0%,95%,74
4.0%,90%,57
6.5%,90%,35"""
    
    st.download_button(
        label="Tải xuống dữ liệu tham khảo (CSV)",
        data=csv,
        file_name="sampling_reference.csv",
        mime="text/csv",
    )
