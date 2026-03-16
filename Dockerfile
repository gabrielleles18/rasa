FROM rasa/rasa-pro:3.10.6

USER root
RUN pip install rasa[full] && \
    python -m spacy download pt_core_news_md
