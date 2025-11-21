import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# 페이지 설정
st.set_page_config(page_title="파크골프 점수 대시보드", layout="wide")

# 제목
st.title("⛳ 파크골프 통합 점수 관리 시스템")
st.markdown("업로드된 CSV 파일을 분석하여 내 점수와 트렌드를 시각화합니다.")

# --------------------------------------------------------------------------
# 데이터 파싱 함수 (파일별 특성 반영)
# --------------------------------------------------------------------------
def parse_score_files():
    all_data = []
    
    # 파일 매핑 (파일명: 구장 별칭)
    files = {
        "점수카드_2025 - 양천생태파골.csv": "양천생태",
        "점수카드_2025 - 소양강.csv": "소양강",
        "점수카드_2025 - 산천어.csv": "화천 산천어",
        "점수카드_2025 - 금천한내.csv": "금천 한내"
    }

    for filename, course_name in files.items():
        if not os.path.exists(filename):
            continue
            
        try:
            # 헤더 없이 원본 그대로 읽기
            df_raw = pd.read_csv(filename, header=None)
            
            current_date = None
            
            # 한 줄씩 읽으며 데이터 추출
            for idx, row in df_raw.iterrows():
                col0 = str(row[0]).strip()
                col1 = str(row[1]).strip()
                
                # 1. 날짜 찾기 (숫자로 시작하고 길이가 6 or 8인 경우)
                # 예: 250525, 20240808, 24.06.02
                date_match = re.match(r'(\d{2,4})[\.|/]?(\d{2})[\.|/]?(\d{2})', col0)
                if date_match and len(col0) >= 6:
                    # 날짜 포맷 통일 (YYYY-MM-DD)
                    raw_date = col0.replace('.', '').replace('/', '')
                    if len(raw_date) == 6: # 250525 -> 2025-05-25
                        current_date = f"20{raw_date[:2]}-{raw_date[2:4]}-{raw_date[4:]}"
                    elif len(raw_date) == 8: # 20240808 -> 2024-08-08
                        current_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                    continue

                # 2. 점수 행 찾기
                # 이름이 있고(문자열), TTL(2번째열)이 숫자인 경우
                if col0 and col0 not in ['nan', 'TTL', '이름', 'None']:
                    try:
                        ttl_score = float(col1)
                        # 점수가 0이거나 너무 큰 경우(거리 표시 등) 제외
                        if 30 <= ttl_score <= 150: 
                            all_data.append({
                                "날짜": current_date if current_date else "날짜미상",
                                "구장": course_name,
                                "이름": col0,
                                "총점": int(ttl_score)
                            })
                    except ValueError:
                        continue # TTL이 숫자가 아님
                        
        except Exception as e:
            st.warning(f"{filename} 처리 중 오류 발생: {e}")

    return pd.DataFrame(all_data)

# --------------------------------------------------------------------------
# 메인 앱 로직
# --------------------------------------------------------------------------

# 데이터 로드
df = parse_score_files()

if df.empty:
    st.error("데이터를 찾을 수 없습니다. CSV 파일이 같은 폴더에 있는지 확인해주세요.")
else:
    # 날짜 형식 변환
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.sort_values('날짜')

    # 사이드바 필터
    st.sidebar.header("검색 필터")
    
    # 이름 선택 (기본값: 가장 기록이 많은 사람)
    top_player = df['이름'].value_counts().idxmax()
    selected_player = st.sidebar.selectbox("선수 선택", ["전체보기"] + list(df['이름'].unique()), index=1)
    
    # 구장 선택
    selected_course = st.sidebar.multiselect("구장 선택", df['구장'].unique(), default=df['구장'].unique())

    # 데이터 필터링
    filtered_df = df[df['구장'].isin(selected_course)]
    if selected_player != "전체보기":
        filtered_df = filtered_df[filtered_df['이름'] == selected_player]

    # --- 대시보드 구성 ---
    
    # 1. 상단 요약 지표
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 라운딩 횟수", f"{len(filtered_df)} 회")
    with col2:
        avg_score = filtered_df['총점'].mean()
        st.metric("평균 타수", f"{avg_score:.1f} 타")
    with col3:
        best_score = filtered_df['총점'].min()
        st.metric("최고 기록 (Best)", f"{best_score} 타")
    with col4:
        recent_score = filtered_df.iloc[-1]['총점'] if not filtered_df.empty else 0
        st.metric("최근 점수", f"{recent_score} 타")

    st.divider()

    # 2. 탭 구성
    tab1, tab2, tab3 = st.tabs(["📈 성적 분석", "📊 구장별 통계", "📝 전체 기록"])

    with tab1:
        st.subheader(f"{selected_player}님의 점수 변화 추이")
        if not filtered_df.empty:
            # 라인 차트
            fig_trend = px.line(filtered_df, x='날짜', y='총점', color='구장', markers=True,
                                title="날짜별 타수 변화 (낮을수록 좋음)")
            fig_trend.update_yaxes(autorange="reversed") # 골프는 점수가 낮아야 좋으므로 축 반전
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("표시할 데이터가 없습니다.")

    with tab2:
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("구장별 평균 타수")
            if selected_player != "전체보기":
                course_avg = filtered_df.groupby('구장')['총점'].mean().reset_index()
                fig_bar = px.bar(course_avg, x='구장', y='총점', text_auto='.1f', color='구장')
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("선수를 선택하면 구장별 평균이 표시됩니다.")

        with col_b:
            st.subheader("타수 분포 (일관성 확인)")
            # 박스 플롯 (일관성 확인용)
            fig_box = px.box(filtered_df, x='구장', y='총점', color='구장')
            fig_box.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_box, use_container_width=True)

    with tab3:
        st.subheader("상세 기록표")
        # 데이터프레임 표시 (날짜 역순)
        display_df = filtered_df[['날짜', '구장', '이름', '총점']].sort_values('날짜', ascending=False)
        display_df['날짜'] = display_df['날짜'].dt.strftime('%Y-%m-%d') # 보기 좋게 포맷팅
        st.dataframe(display_df, use_container_width=True)
        
        # CSV 다운로드 버튼
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("결과 CSV 다운로드", csv, "my_parkgolf_records.csv", "text/csv")
