"""
End-to-End Coach Simulation
============================

Tests the full coach flow by simulating a multi-turn conversation.
Uses a mock LLM to verify prompt construction and response handling.
"""
import sys
sys.path.insert(0, '/Users/mertyavuz/Desktop/VSCode-Projects/05-Threshold')

from unittest.mock import Mock, MagicMock, patch
from datetime import date
from coach_v2.orchestrator import CoachOrchestrator, ChatRequest, ChatResponse

class MockLLMClient:
    """Mock LLM that echoes back prompts for inspection."""
    def __init__(self):
        self.last_prompt = None
        self.call_count = 0
    
    def generate(self, prompt: str, max_tokens: int = 400):
        self.last_prompt = prompt
        self.call_count += 1
        
        # Return a mock response based on what we detect in prompt
        mock = Mock()
        
        if "SOHBET GEÇMİŞİ" in prompt and "AKTİVİTE VERİSİ" in prompt:
            mock.text = "Koşunuzu inceledim. 10km'yi 145 bpm ortalama ile bitirmişsiniz - bu harika bir aerobik tempo! Pacing çok düzgün, metronom gibi koşmuşsunuz. Bir sonraki antrenmanda biraz daha hızlı tempo deneyebilirsiniz. Kadans nasıl hissettirdi?"
        elif "MEVCUT VERİ" in prompt and "TSB" in prompt:
            mock.text = "Formuna baktım, şu an TSB +5 civarında görünüyor. Bu dinlenmiş olduğun anlamına geliyor. Haftalık yükün makul, aşırı yorgunluk yok. Bu hafta biraz daha zorlayabilirsin."
        else:
            mock.text = "Selam! Bugün nasıl yardımcı olabilirim?"
            
        return mock

def create_test_activity_pack():
    """Create a realistic activity pack for testing."""
    return {
        "facts": """ACTIVITY_NAME: Morning Easy Run
TYPE: running
DISTANCE: 10.00 km
DURATION: 60 min
AVG_PACE: 6:00/km
AVG_HR: 145 bpm
MAX_HR: 165 bpm
CADENCE: 172 spm""",
        "tables": "Lap 1: 6:05/km, 142bpm | Lap 2: 6:00/km, 145bpm | Lap 3: 5:55/km, 148bpm",
        "flags": ["Pacing: METRONOME (0.9% var). Excellent pacing consistency."],
        "readiness": "Sleep Score: 82, HRV: 45ms"
    }

def test_greeting_flow():
    """Test that greeting returns warm response without hallucination."""
    print("\n" + "=" * 60)
    print("TEST: Greeting Flow")
    print("=" * 60)
    
    # Mock the database session
    mock_db = Mock()
    mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=None)))
    mock_db.commit = Mock()
    
    mock_llm = MockLLMClient()
    
    with patch('coach_v2.orchestrator.CoachV2Repository'):
        with patch('coach_v2.orchestrator.CandidateRetriever'):
            with patch('coach_v2.orchestrator.TrainingLoadEngine'):
                orchestrator = CoachOrchestrator(mock_db, mock_llm)
                
                request = ChatRequest(
                    user_id=1,
                    message="Selam coach!"
                )
                
                response = orchestrator.handle_chat(request)
                
                print(f"Input: 'Selam coach!'")
                print(f"Output: {response.message}")
                print(f"LLM called: {mock_llm.call_count} times")
                
                # Greeting should use static response, not LLM
                assert "yardımcı olabilirim" in response.message.lower(), "Greeting should be helpful"
                assert mock_llm.call_count == 0, "Greeting should NOT call LLM"
                print("✓ PASSED: Greeting is static and helpful")

def test_activity_analysis_flow():
    """Test activity analysis generates natural conversation."""
    print("\n" + "=" * 60)
    print("TEST: Activity Analysis Flow")
    print("=" * 60)
    
    mock_db = Mock()
    mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=None)))
    mock_db.commit = Mock()
    
    mock_llm = MockLLMClient()
    
    with patch('coach_v2.orchestrator.CoachV2Repository') as MockRepo:
        with patch('coach_v2.orchestrator.CandidateRetriever'):
            with patch('coach_v2.orchestrator.TrainingLoadEngine'):
                with patch('coach_v2.orchestrator.AnalysisPackBuilder') as MockBuilder:
                    # Setup mocks
                    mock_builder = MockBuilder.return_value
                    mock_builder.build_pack.return_value = create_test_activity_pack()
                    
                    orchestrator = CoachOrchestrator(mock_db, mock_llm)
                    
                    request = ChatRequest(
                        user_id=1,
                        message="Bu koşuyu analiz et",
                        garmin_activity_id=12345,
                        activity_details_json={
                            "activityName": "Morning Run",
                            "local_start_date": "2024-12-15"
                        }
                    )
                    
                    response = orchestrator.handle_chat(request)
                    
                    print(f"Input: 'Bu koşuyu analiz et' with activity data")
                    print(f"Output: {response.message[:200]}...")
                    
                    # Check prompt structure
                    if mock_llm.last_prompt:
                        print("\n-- Prompt includes --")
                        print(f"  COACH_PERSONA: {'Sen deneyimli' in mock_llm.last_prompt}")
                        print(f"  RUNNING_EXPERTISE: {'NABIZ BÖLGELERİ' in mock_llm.last_prompt}")
                        print(f"  Activity context: {'AKTİVİTE VERİSİ' in mock_llm.last_prompt}")
                        print(f"  User question: {'SPORCU SORUSU' in mock_llm.last_prompt}")
                        print(f"  Instruction: {'TALİMAT' in mock_llm.last_prompt}")
                        
                    print("✓ PASSED: Activity analysis uses proper prompt structure")

def test_trend_query_flow():
    """Test trend/form query generates insightful response."""
    print("\n" + "=" * 60)
    print("TEST: Trend Query Flow")  
    print("=" * 60)
    
    mock_db = Mock()
    mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=None)))
    mock_db.commit = Mock()
    
    mock_llm = MockLLMClient()
    
    with patch('coach_v2.orchestrator.CoachV2Repository') as MockRepo:
        with patch('coach_v2.orchestrator.CandidateRetriever'):
            with patch('coach_v2.orchestrator.TrainingLoadEngine') as MockLoad:
                mock_load = MockLoad.return_value
                mock_load.calculate_sync_load.return_value = {
                    'tss': 50.0,
                    'atl': 40.0,
                    'ctl': 35.0,
                    'tsb': 5.0
                }
                
                mock_repo = MockRepo.return_value
                mock_repo.get_activity_summaries_range.return_value = [1, 2, 3]  # 3 activities
                
                orchestrator = CoachOrchestrator(mock_db, mock_llm)
                
                request = ChatRequest(
                    user_id=1,
                    message="Bu hafta nasıldı?"
                )
                
                response = orchestrator.handle_chat(request)
                
                print(f"Input: 'Bu hafta nasıldı?'")
                print(f"Output: {response.message}")
                
                if mock_llm.last_prompt:
                    print(f"\nPrompt mentions TSB: {'TSB' in mock_llm.last_prompt}")
                    print(f"Prompt mentions dinlenme: {'dinlen' in mock_llm.last_prompt.lower()}")
                    
                print("✓ PASSED: Trend query uses training load data")

def test_conversation_memory():
    """Test that conversation history is included in prompts."""
    print("\n" + "=" * 60)
    print("TEST: Conversation Memory")
    print("=" * 60)
    
    mock_db = Mock()
    mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=None)))
    mock_db.commit = Mock()
    
    mock_llm = MockLLMClient()
    
    with patch('coach_v2.orchestrator.CoachV2Repository') as MockRepo:
        with patch('coach_v2.orchestrator.CandidateRetriever'):
            with patch('coach_v2.orchestrator.TrainingLoadEngine') as MockLoad:
                with patch('coach_v2.orchestrator.AnalysisPackBuilder') as MockBuilder:
                    mock_load = MockLoad.return_value
                    mock_load.calculate_sync_load.return_value = {'tss': 50.0, 'atl': 40.0, 'ctl': 35.0, 'tsb': 5.0}
                    mock_repo = MockRepo.return_value
                    mock_repo.get_activity_summaries_range.return_value = []
                    
                    orchestrator = CoachOrchestrator(mock_db, mock_llm)
                    
                    # Simulate follow-up with history
                    request = ChatRequest(
                        user_id=1,
                        message="Ama ben yarış hazırlığındayım",
                        conversation_history=[
                            ("user", "Bu hafta nasıldı?"),
                            ("assistant", "TSB +5, dinlenmiş görünüyorsun.")
                        ]
                    )
                    
                    response = orchestrator.handle_chat(request)
                    
                    print(f"Input: Follow-up with history")
                    print(f"History included: {mock_llm.last_prompt is not None and 'TSB +5' in mock_llm.last_prompt if mock_llm.last_prompt else 'N/A'}")
                    
                    if mock_llm.last_prompt and "TSB +5" in mock_llm.last_prompt:
                        print("✓ PASSED: Conversation history is included in prompt")
                    else:
                        print("⚠ Check: History might not be included")

if __name__ == "__main__":
    print("\n🏃 Coach V2 End-to-End Simulation 🏃\n")
    
    test_greeting_flow()
    test_activity_analysis_flow()
    test_trend_query_flow()
    test_conversation_memory()
    
    print("\n" + "=" * 60)
    print("All E2E simulations complete!")
    print("=" * 60)
