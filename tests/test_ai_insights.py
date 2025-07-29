import pytest
import json
import numpy as np
from app.ai_insights import AnalyticsProcessor


class TestAIInsights:
    """Test AI insights functionality"""
    
    @pytest.fixture
    def analytics_processor(self):
        """Create AI insights instance for testing"""
        return AnalyticsProcessor()
    
    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript for testing"""
        return """Agent: Hello, how can I help you today?
Customer: I'm interested in your product.
Agent: Great! Let me tell you about our features.
Customer: What are the pricing options?
Agent: I'd be happy to discuss our pricing with you."""
    
    def test_agent_talk_ratio(self, analytics_processor, sample_transcript):
        """Test agent talk ratio calculation"""
        ratio = analytics_processor.agent_talk_ratio(sample_transcript)
        
        assert isinstance(ratio, float)
        assert 0 <= ratio <= 1
        
        # Should be around 0.6-0.7 for this transcript
        assert ratio > 0.5
    
    def test_customer_sentiment(self, analytics_processor):
        """Test sentiment analysis"""
        # Test positive sentiment
        positive_text = "Customer: I am very happy with the service."
        sentiment = analytics_processor.customer_sentiment(positive_text)
        assert isinstance(sentiment, float)
        assert sentiment > 0
        
        # Test negative sentiment
        negative_text = "Customer: I am very unhappy with the service."
        sentiment = analytics_processor.customer_sentiment(negative_text)
        assert isinstance(sentiment, float)
        assert sentiment < 0
    
    def test_transcript_embedding(self, analytics_processor, sample_transcript):
        """Test embedding generation"""
        embedding = analytics_processor.transcript_embedding(sample_transcript)
        
        assert isinstance(embedding, str)
        
        # Should be valid JSON
        embedding_list = json.loads(embedding)
        assert isinstance(embedding_list, list)
        assert len(embedding_list) > 0
        
        # All values should be numbers
        for value in embedding_list:
            assert isinstance(value, (int, float))
    
    def test_cosine_similarity(self, analytics_processor):
        """Test similarity calculation"""
        # Create two similar embeddings
        embedding1 = '[0.1, 0.2, 0.3, 0.4]'
        embedding2 = '[0.1, 0.2, 0.3, 0.4]'
        
        similarity = analytics_processor.cosine_similarity(embedding1, embedding2)
        
        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1
        
        # Similar embeddings should have high similarity
        assert similarity == 1.0
    
    def test_cosine_similarity_identical(self, analytics_processor):
        """Test similarity calculation with identical embeddings"""
        embedding = '[0.1, 0.2, 0.3, 0.4]'
        
        similarity = analytics_processor.cosine_similarity(embedding, embedding)
        
        assert similarity == 1.0
    
    def test_cosine_similarity_zero_vectors(self, analytics_processor):
        """Test similarity calculation with zero vectors"""
        embedding1 = '[0.0, 0.0, 0.0, 0.0]'
        embedding2 = '[0.0, 0.0, 0.0, 0.0]'
        
        similarity = analytics_processor.cosine_similarity(embedding1, embedding2)
        
        assert similarity == 0.0
    
    def test_process(self, analytics_processor, sample_transcript):
        """Test complete call processing"""
        agent_ratio, sentiment_score, embedding = analytics_processor.process(sample_transcript)
        
        # Check agent ratio
        assert isinstance(agent_ratio, float)
        assert 0 <= agent_ratio <= 1
        
        # Check sentiment score
        assert isinstance(sentiment_score, float)
        assert -1 <= sentiment_score <= 1
        
        # Check embedding
        assert isinstance(embedding, str)
        embedding_list = json.loads(embedding)
        assert isinstance(embedding_list, list)
        assert len(embedding_list) > 0
    
    def test_empty_transcript(self, analytics_processor):
        """Test processing empty transcript"""
        agent_ratio, sentiment_score, embedding = analytics_processor.process("")
        
        assert agent_ratio == 0.0
        assert sentiment_score == 0.0
        assert isinstance(embedding, str)
    
    def test_transcript_without_customer_speech(self, analytics_processor):
        """Test transcript with only agent speech"""
        transcript = "Agent: Hello, how can I help you?"
        
        agent_ratio, sentiment_score, embedding = analytics_processor.process(transcript)
        
        assert agent_ratio > 0  # All words are agent words
        assert sentiment_score == 0.0  # No customer speech
        assert isinstance(embedding, str)
    
    def test_transcript_without_agent_speech(self, analytics_processor):
        """Test transcript with only customer speech"""
        transcript = "Customer: I need help with my order."
        
        agent_ratio, sentiment_score, embedding = analytics_processor.process(transcript)
        
        assert agent_ratio == 0.0  # No agent words
        assert sentiment_score != 0.0
        assert isinstance(embedding, str) 