FROM rasa/rasa-pro:3.10.6

USER root
RUN pip install rasa[full]
