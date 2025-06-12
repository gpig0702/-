import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="나노융합기술 유사도 네트워크", layout="wide")
st.title("🔬 나노융합기술 100선 – 유사도 네트워크 시각화")

csv_url = "https://raw.githubusercontent.com/gpig0702/20025.06.02/main/kimm_nano_100.csv"

try:
    df = pd.read_csv(csv_url, encoding="utf-8")
    st.success("✅ CSV 파일을 성공적으로 불러왔습니다.")
except Exception as e:
    st.error(f"❌ CSV 불러오기 실패: {e}")
    st.stop()

text_col = st.selectbox("기술 설명이 포함된 열을 선택하세요", df.columns)

threshold = st.slider(
    "유사도 임계값 (0.0 ~ 1.0)",
    min_value=0.0,
    max_value=1.0,
    value=0.3,
    step=0.05
)

search_keyword = st.text_input("🔍 특정 키워드로 관련 기술만 필터링 (선택사항)", "").strip()

texts = df[text_col].fillna("").astype(str).tolist()
vectorizer = TfidfVectorizer()
try:
    tfidf_matrix = vectorizer.fit_transform(texts)
except Exception as e:
    st.error(f"TF-IDF 처리 실패: {e}")
    st.stop()

similarity_matrix = cosine_similarity(tfidf_matrix)

G = nx.Graph()
for i, txt in enumerate(texts):
    G.add_node(i, label=txt)

for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        if similarity_matrix[i][j] >= threshold:
            G.add_edge(i, j, weight=float(similarity_matrix[i][j]))

if G.number_of_nodes() == 0:
    st.warning("데이터가 존재하지 않습니다. 컬럼과 CSV 내용을 확인하세요.")
    st.stop()
if G.number_of_edges() == 0:
    st.warning("간선이 없습니다. 임계값을 낮춰보세요.")
    st.stop()

# 🔍 필터링: 검색 키워드가 있을 경우 해당 노드와 연결된 노드만 표시
if search_keyword:
    matched_nodes = [n for n, d in G.nodes(data=True) if search_keyword in d["label"]]
    if matched_nodes:
        sub_nodes = set()
        for node in matched_nodes:
            sub_nodes.add(node)
            sub_nodes.update(G.neighbors(node))
        G = G.subgraph(sub_nodes).copy()
    else:
        st.warning("검색된 키워드에 해당하는 기술이 없습니다.")
        st.stop()

# 레이아웃
pos = nx.spring_layout(G, seed=42)

node_x, node_y, node_text, node_hover, node_degrees = [], [], [], [], []
for n in G.nodes():
    x, y = pos[n]
    label = G.nodes[n]["label"]
    short_label = label[:15] + "..." if len(label) > 15 else label
    node_x.append(x); node_y.append(y)
    node_text.append(short_label)
    node_hover.append(label)
    node_degrees.append(len(list(G.neighbors(n))))

edge_x, edge_y = [], []
for e in G.edges():
    x0, y0 = pos[e[0]]
    x1, y1 = pos[e[1]]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

edge_trace = go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(width=0.5, color="#888"), hoverinfo="none"
)

node_trace = go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    text=node_text, hovertext=node_hover, textposition="top center",
    hoverinfo="text",
    marker=dict(
        showscale=True, colorscale="YlGnBu", reversescale=True,
        color=node_degrees, size=10, line_width=2,
        colorbar=dict(title="연결 수", thickness=15, xanchor="left")
    )
)

fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title="기술 유사도 기반 네트워크",
                    titlefont_size=20, showlegend=False,
                    hovermode="closest",
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                ))
st.plotly_chart(fig, use_container_width=True)

# 📊 유사도 상위 기술쌍 출력
st.subheader("📋 유사도 상위 기술쌍 (Top 20)")
top_n = 20
pairs = []
for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        score = similarity_matrix[i][j]
        if score >= threshold:
            pairs.append((i, j, score))

top_pairs = sorted(pairs, key=lambda x: x[2], reverse=True)[:top_n]

top_df = pd.DataFrame([
    {
        "기술 A": texts[i],
        "기술 B": texts[j],
        "유사도": round(score, 3)
    }
    for i, j, score in top_pairs
])
st.dataframe(top_df, use_container_width=True)
