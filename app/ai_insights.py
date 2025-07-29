import json
import numpy as np
from typing import Tuple, List
import hashlib
import random
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from app.config import settings

class AnalyticsProcessor:
    def __init__(self):
        try:
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            self.sentiment_model = pipeline("sentiment-analysis", model=settings.sentiment_model)
            self.embedding_size = 384
        except Exception as e:
            self.embedding_model = None
            self.sentiment_model = None
            self.embedding_size = 384
    def agent_talk_ratio(self, transcript: str) -> float:
        lines = transcript.strip().split('\n')
        agent_words = 0
        total_words = 0
        for line in lines:
            if line.strip():
                if line.strip().startswith('Agent:'):
                    words = line.replace('Agent:', '').strip().split()
                    agent_words += len(words)
                total_words += len(line.split())
        return agent_words / total_words if total_words > 0 else 0.0
    def customer_sentiment(self, transcript: str) -> float:
        if self.sentiment_model is None:
            return self._customer_sentiment_simple(transcript)
        try:
            customer_lines = []
            for line in transcript.strip().split('\n'):
                if line.strip().startswith('Customer:'):
                    customer_lines.append(line.replace('Customer:', '').strip())
            if not customer_lines:
                return 0.0
            customer_text = ' '.join(customer_lines)
            result = self.sentiment_model(customer_text)
            label = result[0]['label'].lower()
            score = result[0]['score']
            if 'positive' in label or 'pos' in label:
                return score
            elif 'negative' in label or 'neg' in label:
                return -score
            else:
                return 0.0
        except Exception:
            return self._customer_sentiment_simple(transcript)
    def _customer_sentiment_simple(self, transcript: str) -> float:
        customer_lines = []
        for line in transcript.strip().split('\n'):
            if line.strip().startswith('Customer:'):
                customer_lines.append(line.replace('Customer:', '').strip())
        if not customer_lines:
            return 0.0
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'like', 'happy', 'satisfied', 'perfect']
        negative_words = ['bad', 'terrible', 'hate', 'dislike', 'unhappy', 'dissatisfied', 'awful', 'horrible']
        customer_text = ' '.join(customer_lines).lower()
        positive_count = sum(1 for word in positive_words if word in customer_text)
        negative_count = sum(1 for word in negative_words if word in customer_text)
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0
        sentiment_score = (positive_count - negative_count) / total_sentiment_words
        return max(-1.0, min(1.0, sentiment_score))
    def transcript_embedding(self, transcript: str) -> str:
        if self.embedding_model is None:
            return self._transcript_embedding_simple(transcript)
        try:
            embedding = self.embedding_model.encode(transcript)
            return json.dumps(embedding.tolist())
        except Exception:
            return self._transcript_embedding_simple(transcript)
    def _transcript_embedding_simple(self, transcript: str) -> str:
        hash_obj = hashlib.md5(transcript.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4]
            while len(chunk) < 4:
                chunk += b'\x00'
            value = int.from_bytes(chunk, byteorder='big')
            normalized_value = (value / (2**32 - 1)) * 2 - 1
            embedding.append(normalized_value)
        while len(embedding) < self.embedding_size:
            embedding.append(0.0)
        embedding = embedding[:self.embedding_size]
        return json.dumps(embedding)
    def cosine_similarity(self, embedding1: str, embedding2: str) -> float:
        vec1 = np.array(json.loads(embedding1))
        vec2 = np.array(json.loads(embedding2))
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    def process(self, transcript: str) -> Tuple[float, float, str]:
        agent_ratio = self.agent_talk_ratio(transcript)
        sentiment_score = self.customer_sentiment(transcript)
        embedding = self.transcript_embedding(transcript)
        return agent_ratio, sentiment_score, embedding
analytics_processor = AnalyticsProcessor() 