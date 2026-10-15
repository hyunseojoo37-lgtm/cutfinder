import os
import re
import json
import csv
import io
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
st.set_page_config(page_title='CutFinder | 숏츠 장면 발굴기', page_icon='🎬', layout='wide')
st.title('🎬 CutFinder')
st.caption('제목과 회차만으로 공개 웹 자료를 조사해 숏츠 후보를 찾습니다. 영상 자체를 시청하는 도구는 아닙니다.')

CATEGORIES=['감동·인류애','사이다·역전','충격·반전','웃음·티키타카','긴장·대립','설렘·로맨스']

def search_web(query, key, max_results=6):
    response=requests.post('https://api.tavily.com/search',json={'api_key':key,'query':query,'search_depth':'advanced','max_results':max_results,'include_answer':False},timeout=35)
    response.raise_for_status()
    results=[]
    for item in response.json().get('results',[]):
        url=item.get('url','')
        if url.startswith(('https://','http://')):
            results.append({'title':item.get('title',''),'url':url,'content':item.get('content','')[:4000]})
    return results

def analyze(drama,season,episode,categories,results,openai_key,model):
    source_lines=[]
    for i,r in enumerate(results,1):
        source_lines.append(f'[{i}] {r["title"]}\nURL: {r["url"]}\n본문: {r["content"]}')
    instructions='''당신은 드라마 숏츠 장면 발굴을 위한 엄격한 리서치 편집자입니다.
검색된 출처에 구체적으로 언급된 해당 시즌/회차의 사건만 후보로 추출합니다. 다른 회차 사건, 등장인물/행동의 추측, 없는 장면, 없는 타임코드를 만들어내지 마세요.
자료가 불충분하면 후보를 적게 출력하거나 0개 출력하세요. 후보 10개를 억지로 채우지 마세요.
각 후보에 source_ids로 실제 근거가 되는 출처 번호를 넣으세요. 적어도 하나의 출처에서 해당 사건을 직접 뒷받침해야 합니다.
공식 영상의 정확한 타임코드가 출처에 명시되지 않았다면 timestamp는 null, location은 '위치 미확인'으로 표시하세요. 초중후반 위치도 근거가 있을 때만 사용하세요.
숏츠 적합도는 편집 가설에 대한 휴리스틱 점수일 뿐 실제 조회수 예측이 아닙니다. 점수는 0~100 정수로 평가하세요.
장면 유형은 요청한 것만 선택하세요. 인용 대사는 창작하지 말고, 후킹 문구는 원문 인용이 아닌 창작 제안으로 작성하세요.
JSON 객체만 출력하세요. 형태: {"episode_summary":"...", "candidates":[{"title":"...","category":"...","score":80,"location":"위치 미확인","timestamp":null,"description":"...","reason":"...","hook":"...","edit_plan":"...","source_ids":[1]}],"limitations":"..."}'''
    user=f'드라마: {drama}\n시즌: {season}\n회차: {episode}\n유형: {", ".join(categories)}\n최대 후보 수: 10\n\n검색 자료:\n'+ '\n\n'.join(source_lines)
    client=OpenAI(api_key=openai_key,timeout=90)
    response=client.chat.completions.create(model=model,messages=[{'role':'system','content':instructions},{'role':'user','content':user}],response_format={'type':'json_object'},temperature=0.2)
    data=json.loads(response.choices[0].message.content)
    clean=[]
    for c in data.get('candidates',[]):
        if not isinstance(c,dict):continue
        ids=[x for x in c.get('source_ids',[]) if isinstance(x,int) and 1<=x<=len(results)]
        if not ids:continue
        c['source_ids']=ids
        try:c['score']=max(0,min(100,int(c.get('score',0))))
        except (ValueError,TypeError):c['score']=0
        clean.append(c)
    data['candidates']=sorted(clean,key=lambda c:c['score'],reverse=True)[:10]
    return data

def to_csv(candidates,results):
    out=io.StringIO()
    fields=['순위','장면','유형','점수','위치','타임코드','장면 설명','추천 이유','후킹','편집 구성','출처 URL']
    writer=csv.DictWriter(out,fieldnames=fields)
    writer.writeheader()
    for i,c in enumerate(candidates,1):
        writer.writerow(dict(zip(fields,[i,c.get('title',''),c.get('category',''),c.get('score',''),c.get('location',''),c.get('timestamp') or '',c.get('description',''),c.get('reason',''),c.get('hook',''),c.get('edit_plan',''),' | '.join(results[j-1]['url'] for j in c['source_ids'])])))
    return '\ufeff'+out.getvalue()

with st.sidebar:
    st.header('🔑 API 설정')
    def secret(name):
        try:return st.secrets.get(name,'')
        except Exception:return ''
    openai_key=st.text_input('OpenAI API Key',value=os.getenv('OPENAI_API_KEY') or secret('OPENAI_API_KEY'),type='password')
    tavily_key=st.text_input('Tavily API Key',value=os.getenv('TAVILY_API_KEY') or secret('TAVILY_API_KEY'),type='password')
    model=st.text_input('AI 모델',value=os.getenv('OPENAI_MODEL') or secret('OPENAI_MODEL') or 'gpt-4.1-mini')
    st.caption('키는 분석 요청에만 사용합니다. 공용 서버에서는 Secrets 설정을 권장합니다. API 호출은 각 서비스에서 과금될 수 있습니다.')

with st.form('search_form'):
    drama=st.text_input('드라마 제목',placeholder='예: 약한영웅 Class 2')
    a,b=st.columns(2)
    with a:season=st.number_input('시즌',min_value=1,max_value=30,value=1,step=1)
    with b:episode=st.number_input('회차',min_value=1,max_value=200,value=1,step=1)
    categories=st.multiselect('찾을 장면 유형',CATEGORIES,default=CATEGORIES[:4])
    submitted=st.form_submit_button('🔍 공개 자료 검색하고 TOP 10 찾기',type='primary',use_container_width=True)

if submitted:
    if not drama.strip():st.error('드라마 제목을 입력해 주세요.')
    elif not categories:st.error('장면 유형을 하나 이상 선택해 주세요.')
    elif not openai_key or not tavily_key:st.error('사이드바에 OpenAI 및 Tavily API 키를 입력해 주세요.')
    else:
        queries=[f'"{drama}" 시즌 {season} {episode}화 줄거리 장면 리뷰',f'"{drama}" season {season} episode {episode} recap key scenes',f'"{drama}" {episode}화 공식 클립 명장면']
        try:
            with st.spinner('웹에서 회차별 자료를 검색하는 중...'):
                found=[]
                for q in queries:
                    found.extend(search_web(q,tavily_key))
                seen=set(); results=[]
                for r in found:
                    if r['url'] not in seen:
                        seen.add(r['url']);results.append(r)
                results=results[:16]
            if not results:st.warning('관련 공개 자료를 찾지 못했습니다. 다른 제목 표기를 시도해 주세요.')
            else:
                with st.spinner('근거를 확인하며 숏츠 후보를 평가하는 중...'):
                    data=analyze(drama,season,episode,categories,results,openai_key,model)
                st.session_state['analysis']={'data':data,'results':results,'label':f'{drama} S{season}E{episode}'}
        except requests.HTTPError as e:st.error(f'웹 검색 API 오류: {e}')
        except Exception as e:st.error(f'분석 실패: {type(e).__name__}: {str(e)[:300]}')

if 'analysis' in st.session_state:
    analysis=st.session_state['analysis'];data=analysis['data'];results=analysis['results'];candidates=data['candidates']
    st.divider();st.subheader(f'📋 {analysis["label"]} 분석 결과')
    st.write(data.get('episode_summary',''))
    st.info(f'근거가 확인된 후보 {len(candidates)}개 · 검색 자료 {len(results)}건. 타임코드는 출처에 명시된 경우에만 표시합니다.')
    if not candidates:st.warning('확인 가능한 후보가 없습니다. 회차 리뷰 또는 공식 클립이 부족할 수 있습니다.')
    for i,c in enumerate(candidates,1):
        with st.expander(f'{i}. {c.get("title","제목 없음")}  |  {c.get("score",0)}점  |  {c.get("category","")}',expanded=i==1):
            st.write('**장면 위치:**',c.get('timestamp') or c.get('location','위치 미확인'))
            st.write('**내용:**',c.get('description',''))
            st.write('**추천 이유:**',c.get('reason',''))
            st.write('**후킹:**',c.get('hook',''))
            st.write('**편집 구상:**',c.get('edit_plan',''))
            st.markdown('**근거 자료:**')
            for j in c['source_ids']:
                r=results[j-1]
                st.markdown(f'- [{r["title"] or urlparse(r["url"]).netloc}]({r["url"]})')
    st.download_button('⬇️ 후보 CSV 다운로드',data=to_csv(candidates,results),file_name='cutfinder_candidates.csv',mime='text/csv',use_container_width=True)
    with st.expander('검색에 사용한 공개 자료'):
        for i,r in enumerate(results,1):st.markdown(f'{i}. [{r["title"]}]({r["url"]})')
    st.caption('⚠️ AI가 출처를 잘못 해석할 수 있으므로 원문과 실제 영상을 확인하세요. 숏츠 제작·게시 시 원본 영상 저작권과 플랫폼 정책을 확인해야 합니다.')
    if data.get('limitations'):st.caption('분석 한계: '+data['limitations'])
