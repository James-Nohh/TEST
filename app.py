import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="화장품 시제품 안정성 대시보드", layout="wide")
st.title("🧴 화장품 시제품 안정성 분석 대시보드")

# 파일 업로드
uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=["xlsx"])

if uploaded_file is None:
    st.info("엑셀 파일을 업로드하면 대시보드가 표시됩니다.")
    st.stop()

# 데이터 로드
df_product = pd.read_excel(uploaded_file, sheet_name="시제품정보")
df_test = pd.read_excel(uploaded_file, sheet_name="안정성테스트결과")

# 병합 데이터
df_merged = df_test.merge(df_product, on="시제품코드", how="left")

# ── 사이드바 필터 ──
st.sidebar.header("필터")
sel_product = st.sidebar.multiselect("시제품코드", df_product["시제품코드"].unique(), default=df_product["시제품코드"].unique())
sel_condition = st.sidebar.multiselect("테스트조건", df_test["테스트조건"].unique(), default=df_test["테스트조건"].unique())
sel_result = st.sidebar.multiselect("판정결과", df_test["판정결과"].unique(), default=df_test["판정결과"].unique())

df_filtered = df_merged[
    (df_merged["시제품코드"].isin(sel_product)) &
    (df_merged["테스트조건"].isin(sel_condition)) &
    (df_merged["판정결과"].isin(sel_result))
]

# ── KPI 카드 ──
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
total_tests = len(df_filtered)
pass_count = (df_filtered["판정결과"] == "적합").sum()
pass_rate = pass_count / total_tests * 100 if total_tests > 0 else 0
review_count = (df_filtered["판정결과"] == "재검토").sum()
avg_ph = df_filtered["pH"].mean() if total_tests > 0 else 0
avg_viscosity = df_filtered["점도_cP"].mean() if total_tests > 0 else 0

col1.metric("총 테스트 건수", f"{total_tests}건")
col2.metric("적합률", f"{pass_rate:.1f}%")
col3.metric("재검토 건수", f"{review_count}건")
col4.metric("평균 pH", f"{avg_ph:.2f}")
col5.metric("평균 점도(cP)", f"{avg_viscosity:,.0f}")

# ── 1행: 판정결과 + 제품유형별 분포 ──
st.markdown("---")
row1_left, row1_right = st.columns(2)

with row1_left:
    st.subheader("판정결과 분포")
    result_counts = df_filtered["판정결과"].value_counts().reset_index()
    result_counts.columns = ["판정결과", "건수"]
    color_map = {"적합": "#2ecc71", "경미변화": "#f39c12", "재검토": "#e74c3c"}
    fig_pie = px.pie(result_counts, names="판정결과", values="건수",
                     color="판정결과", color_discrete_map=color_map, hole=0.4)
    fig_pie.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

with row1_right:
    st.subheader("제품유형별 테스트 건수 및 적합률")
    type_stats = df_filtered.groupby("제품유형").agg(
        건수=("판정결과", "count"),
        적합=("판정결과", lambda x: (x == "적합").sum())
    ).reset_index()
    type_stats["적합률"] = (type_stats["적합"] / type_stats["건수"] * 100).round(1)

    fig_bar = make_subplots(specs=[[{"secondary_y": True}]])
    fig_bar.add_trace(go.Bar(x=type_stats["제품유형"], y=type_stats["건수"], name="테스트 건수", marker_color="#3498db"), secondary_y=False)
    fig_bar.add_trace(go.Scatter(x=type_stats["제품유형"], y=type_stats["적합률"], name="적합률(%)", mode="lines+markers", marker_color="#e74c3c", line=dict(width=3)), secondary_y=True)
    fig_bar.update_yaxes(title_text="건수", secondary_y=False)
    fig_bar.update_yaxes(title_text="적합률(%)", range=[0, 110], secondary_y=True)
    fig_bar.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_bar, use_container_width=True)

# ── 2행: 테스트조건별 pH/점도 분석 ──
st.markdown("---")
row2_left, row2_right = st.columns(2)

with row2_left:
    st.subheader("테스트조건별 pH 분포")
    fig_ph = px.box(df_filtered, x="테스트조건", y="pH", color="테스트조건",
                    points="all", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_ph.update_layout(margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig_ph, use_container_width=True)

with row2_right:
    st.subheader("테스트조건별 점도(cP) 분포")
    fig_vis = px.box(df_filtered, x="테스트조건", y="점도_cP", color="테스트조건",
                     points="all", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_vis.update_layout(margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig_vis, use_container_width=True)

# ── 3행: 보관기간별 추이 + 시제품별 히트맵 ──
st.markdown("---")
row3_left, row3_right = st.columns(2)

with row3_left:
    st.subheader("보관기간별 pH 추이 (시제품별)")
    fig_line = px.line(df_filtered, x="보관기간_주", y="pH",
                       color="시제품코드", markers=True,
                       color_discrete_sequence=px.colors.qualitative.Vivid)
    fig_line.update_layout(margin=dict(t=20, b=20), xaxis_title="보관기간(주)", yaxis_title="pH")
    st.plotly_chart(fig_line, use_container_width=True)

with row3_right:
    st.subheader("시제품 × 테스트조건 적합률 히트맵")
    heatmap_data = df_filtered.groupby(["시제품코드", "테스트조건"]).apply(
        lambda x: (x["판정결과"] == "적합").mean() * 100
    ).reset_index(name="적합률")
    heatmap_pivot = heatmap_data.pivot(index="시제품코드", columns="테스트조건", values="적합률").fillna(0)
    fig_heat = px.imshow(heatmap_pivot, text_auto=".0f", aspect="auto",
                         color_continuous_scale="RdYlGn", zmin=0, zmax=100,
                         labels=dict(color="적합률(%)"))
    fig_heat.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig_heat, use_container_width=True)

# ── 4행: 색상변화 + 향/분리현상 ──
st.markdown("---")
row4_left, row4_right = st.columns(2)

with row4_left:
    st.subheader("시제품별 평균 색상변화등급")
    color_grade = df_filtered.groupby("시제품코드")["색상변화등급"].mean().reset_index()
    color_grade.columns = ["시제품코드", "평균등급"]
    color_grade = color_grade.sort_values("평균등급", ascending=True)
    fig_cg = px.bar(color_grade, x="평균등급", y="시제품코드", orientation="h",
                    color="평균등급", color_continuous_scale="OrRd")
    fig_cg.update_layout(margin=dict(t=20, b=20), yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig_cg, use_container_width=True)

with row4_right:
    st.subheader("향변화 및 분리현상 발생 현황")
    issue_data = df_filtered.groupby("시제품코드").agg(
        향변화=("향변화여부", lambda x: (x == "Y").sum()),
        분리현상=("분리현상여부", lambda x: (x == "Y").sum())
    ).reset_index()
    fig_issue = go.Figure()
    fig_issue.add_trace(go.Bar(x=issue_data["시제품코드"], y=issue_data["향변화"], name="향변화", marker_color="#e74c3c"))
    fig_issue.add_trace(go.Bar(x=issue_data["시제품코드"], y=issue_data["분리현상"], name="분리현상", marker_color="#f39c12"))
    fig_issue.update_layout(barmode="group", margin=dict(t=20, b=20), yaxis_title="발생 건수",
                            legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_issue, use_container_width=True)

# ── 5행: 담당팀별 현황 + 개발단계별 현황 ──
st.markdown("---")
row5_left, row5_right = st.columns(2)

with row5_left:
    st.subheader("담당팀별 테스트 현황")
    team_stats = df_filtered.groupby("담당팀").agg(
        테스트건수=("판정결과", "count"),
        적합건수=("판정결과", lambda x: (x == "적합").sum()),
        재검토건수=("판정결과", lambda x: (x == "재검토").sum())
    ).reset_index()
    team_stats["적합률"] = (team_stats["적합건수"] / team_stats["테스트건수"] * 100).round(1)
    st.dataframe(team_stats, use_container_width=True, hide_index=True)

with row5_right:
    st.subheader("개발단계별 판정결과")
    stage_result = df_filtered.groupby(["개발단계", "판정결과"]).size().reset_index(name="건수")
    fig_stage = px.bar(stage_result, x="개발단계", y="건수", color="판정결과",
                       color_discrete_map=color_map, barmode="stack")
    fig_stage.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_stage, use_container_width=True)

# ── 원본 데이터 테이블 ──
st.markdown("---")
with st.expander("📋 원본 데이터 보기"):
    tab1, tab2, tab3 = st.tabs(["시제품정보", "안정성테스트결과", "병합 데이터"])
    with tab1:
        st.dataframe(df_product, use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df_test, use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
