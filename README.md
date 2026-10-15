# 🎬 CutFinder — 드라마 숏츠 후보 발굴 웹앱

드라마 제목·시즌·회차를 입력하면 **Tavily 검색 API**로 공개 회차 리뷰/줄거리/공식 클립을 찾고, **OpenAI API**로 근거가 있는 장면 후보 최대 10개를 정리하는 Streamlit 웹앱입니다.

## 로컬 실행

Python 3.10 이상 설치 후 프로젝트 폴더에서:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

웹 화면 왼쪽에서 `OPENAI_API_KEY`와 `TAVILY_API_KEY`를 입력하세요. 또는 `.env.example`을 `.env`로 복사한 후 값을 입력할 수 있습니다. **`.env` 파일을 GitHub에 올리지 마세요.**

## 인터넷 웹사이트로 배포하기

1. 이 폴더의 `app.py`, `requirements.txt`, `README.md`를 개인 GitHub 저장소에 올립니다. API 키는 올리지 않습니다.
2. [Streamlit Community Cloud](https://share.streamlit.io/)에서 GitHub 저장소를 연결하고 엔트리 파일을 `app.py`로 지정합니다.
3. 앱 설정의 **Secrets**에 다음을 등록합니다.

```toml
OPENAI_API_KEY = "실제_OpenAI_API_키"
TAVILY_API_KEY = "실제_Tavily_API_키"
OPENAI_MODEL = "gpt-4.1-mini"
```

4. 배포된 URL에서 드라마 제목과 회차를 입력합니다.

> 공개 배포 시 API 키 남용 및 요금 발생에 주의하세요. 이 시제품에는 로그인/사용량 제한이 없으므로 **개인용 비공개 운영**을 권장합니다. Streamlit Community Cloud의 저장소 접근 정책은 배포 시 확인하세요.

## 유의 사항

- AI는 OTT 영상을 직접 보지 않습니다. 검색된 공개 텍스트에 명시된 사건만 후보로 제시하도록 지시되어 있습니다.
- 출처에 시간 정보가 없다면 정확한 타임코드를 제공하지 않습니다.
- 모델의 출처 해석이 완벽하지 않을 수 있으므로 실제 장면과 회차를 확인하세요.
- 검색 결과에 따라 후보가 10개 미만 또는 0개일 수 있습니다.
- API 사용량에 따라 별도 요금이 발생할 수 있습니다.
- 원본 드라마의 저작권과 플랫폼의 재사용·수익화 정책을 확인해야 합니다.
