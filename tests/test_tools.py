"""Unit tests for tools functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.tools.contract_analyzer import ContractAnalyzer
from app.tools.weather_api import WeatherAPI
from app.tools.shipping_tracker import ShippingTracker


class TestContractAnalyzer:
    """Test cases for ContractAnalyzer class."""
    
    def test_analyzer_initialization(self):
        """Test ContractAnalyzer initialization."""
        analyzer = ContractAnalyzer()
        
        assert len(analyzer.key_terms) > 0
        assert "payment terms" in analyzer.key_terms
        assert "liability" in analyzer.key_terms
        assert len(analyzer.risk_indicators) > 0
        assert "unlimited liability" in analyzer.risk_indicators
    
    @pytest.mark.asyncio
    async def test_analyze_terms(self):
        """Test contract terms analysis."""
        analyzer = ContractAnalyzer()
        
        result = await analyzer.analyze_terms(
            "contract_123", 
            "Payment terms dispute regarding 30-day payment period"
        )
        
        assert "contract_id" in result
        assert result["contract_id"] == "contract_123"
        assert "key_terms_found" in result
        assert "risk_assessment" in result
        assert "relevant_clauses" in result
        assert "recommendations" in result
    
    def test_extract_key_terms(self):
        """Test key terms extraction."""
        analyzer = ContractAnalyzer()
        
        text = "The payment terms require settlement within 30 days. Liability is limited to contract value."
        terms = analyzer._extract_key_terms(text)
        
        assert len(terms) >= 2
        payment_terms = [t for t in terms if t["term"] == "payment terms"]
        liability_terms = [t for t in terms if t["term"] == "liability"]
        
        assert len(payment_terms) > 0
        assert len(liability_terms) > 0
    
    def test_assess_risks(self):
        """Test risk assessment."""
        analyzer = ContractAnalyzer()
        
        high_risk_text = "Contract includes unlimited liability and no warranty provisions."
        risks = analyzer._assess_risks(high_risk_text)
        
        assert "total_risks" in risks
        assert "high_risk_count" in risks
        assert "overall_risk_level" in risks
        assert risks["overall_risk_level"] == "high"
    
    def test_identify_relevant_clauses(self):
        """Test relevant clauses identification."""
        analyzer = ContractAnalyzer()
        
        dispute_context = "Payment delay issue"
        clauses = analyzer._identify_relevant_clauses(dispute_context)
        
        assert isinstance(clauses, list)
        assert len(clauses) > 0
        assert all("clause_number" in clause for clause in clauses)
        assert all("relevance_score" in clause for clause in clauses)
    
    @pytest.mark.asyncio
    async def test_compare_contracts(self):
        """Test contract comparison."""
        analyzer = ContractAnalyzer()
        
        result = await analyzer.compare_contracts(["contract_1", "contract_2"])
        
        assert "contracts_compared" in result
        assert "key_differences" in result
        assert "common_terms" in result
        assert "risk_variations" in result
    
    @pytest.mark.asyncio
    async def test_extract_obligations(self):
        """Test obligation extraction."""
        analyzer = ContractAnalyzer()
        
        contract_text = """
        Party A shall deliver goods within 30 days.
        Party B must pay within 15 days of delivery.
        Both parties agree to maintain confidentiality.
        """
        
        result = await analyzer.extract_obligations(contract_text)
        
        assert "party_a_obligations" in result
        assert "party_b_obligations" in result
        assert "mutual_obligations" in result
        assert "conditional_obligations" in result


class TestWeatherAPI:
    """Test cases for WeatherAPI class."""
    
    def test_weather_api_initialization(self):
        """Test WeatherAPI initialization."""
        api = WeatherAPI("test_api_key")
        
        assert api.api_key == "test_api_key"
        assert "openweathermap.org" in api.base_url
    
    @pytest.mark.asyncio
    async def test_get_current_weather_no_api_key(self):
        """Test current weather without API key."""
        api = WeatherAPI()
        
        result = await api.get_current_weather("New York")
        
        assert "error" in result
        assert "API key not configured" in result["error"]
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_get_current_weather_success(self, mock_get):
        """Test successful current weather retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "name": "New York",
            "sys": {"country": "US"},
            "main": {
                "temp": 20.5,
                "feels_like": 22.0,
                "humidity": 65,
                "pressure": 1013
            },
            "wind": {"speed": 5.2, "deg": 180},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "coord": {"lat": 40.7128, "lon": -74.0060}
        })
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = WeatherAPI("test_key")
        result = await api.get_current_weather("New York")
        
        assert "error" not in result
        assert result["location"] == "New York"
        assert result["temperature"] == 20.5
        assert result["weather_main"] == "Clear"
    
    def test_is_severe_weather(self):
        """Test severe weather detection."""
        api = WeatherAPI()
        
        # Test severe wind
        severe_wind = {"wind_speed": 20, "weather_main": "Clear", "visibility": 10, "temperature": 15}
        assert api._is_severe_weather(severe_wind) == True
        
        # Test thunderstorm
        thunderstorm = {"wind_speed": 5, "weather_main": "Thunderstorm", "visibility": 10, "temperature": 20}
        assert api._is_severe_weather(thunderstorm) == True
        
        # Test normal conditions
        normal = {"wind_speed": 5, "weather_main": "Clear", "visibility": 10, "temperature": 20}
        assert api._is_severe_weather(normal) == False
    
    def test_assess_severity(self):
        """Test weather severity assessment."""
        api = WeatherAPI()
        
        extreme_weather = {"wind_speed": 30, "weather_main": "Extreme", "visibility": 0.3}
        assert api._assess_severity(extreme_weather) == "extreme"
        
        severe_weather = {"wind_speed": 18, "weather_main": "Thunderstorm", "visibility": 0.8}
        assert api._assess_severity(severe_weather) == "severe"
        
        moderate_weather = {"wind_speed": 8, "weather_main": "Rain", "visibility": 5}
        assert api._assess_severity(moderate_weather) == "moderate"
    
    def test_assess_weather_impact(self):
        """Test weather impact assessment."""
        api = WeatherAPI()
        
        conditions = [{"date": "2024-01-01"}, {"date": "2024-01-02"}]
        severe_events = [
            {"date": "2024-01-01", "severity": "severe"},
            {"date": "2024-01-02", "severity": "extreme"}
        ]
        
        impact = api._assess_weather_impact(conditions, severe_events)
        
        assert impact["total_days_analyzed"] == 2
        assert impact["severe_weather_days"] == 2
        assert impact["impact_level"] == "high"
        assert impact["force_majeure_applicable"] == True


class TestShippingTracker:
    """Test cases for ShippingTracker class."""
    
    def test_shipping_tracker_initialization(self):
        """Test ShippingTracker initialization."""
        tracker = ShippingTracker()
        
        assert "fedex" in tracker.supported_carriers
        assert "ups" in tracker.supported_carriers
        assert "dhl" in tracker.supported_carriers
        assert "usps" in tracker.supported_carriers
    
    def test_detect_carrier(self):
        """Test carrier detection from tracking numbers."""
        tracker = ShippingTracker()
        
        # Test FedEx format
        fedex_number = "123456789012"
        assert tracker._detect_carrier(fedex_number) == "fedex"
        
        # Test UPS format
        ups_number = "1Z999AA1234567890"
        assert tracker._detect_carrier(ups_number) == "ups"
        
        # Test invalid format
        invalid_number = "INVALID123"
        assert tracker._detect_carrier(invalid_number) is None
    
    @pytest.mark.asyncio
    async def test_track_shipment(self):
        """Test shipment tracking."""
        tracker = ShippingTracker()
        
        # Mock the _fetch_tracking_data method
        tracker._fetch_tracking_data = AsyncMock(return_value={
            "status": "delivered",
            "delivery_date": datetime.utcnow().isoformat(),
            "events": [{"status": "picked_up", "date": datetime.utcnow().isoformat()}]
        })
        
        result = await tracker.track_shipment("123456789012", "fedex")
        
        assert "tracking_number" in result
        assert "carrier" in result
        assert "status" in result
        assert result["carrier"] == "fedex"
    
    @pytest.mark.asyncio
    async def test_verify_delivery(self):
        """Test delivery verification."""
        tracker = ShippingTracker()
        
        # Mock track_shipment method
        delivery_date = datetime.utcnow() - timedelta(days=1)
        tracker.track_shipment = AsyncMock(return_value={
            "tracking_number": "123456789012",
            "status": "delivered",
            "delivery_date": delivery_date.isoformat()
        })
        
        expected_date = datetime.utcnow() - timedelta(days=2)
        result = await tracker.verify_delivery("123456789012", expected_date)
        
        assert "verification_result" in result
        assert "delay_analysis" in result
        assert result["verification_result"] == "delivered"
    
    def test_categorize_delay(self):
        """Test delay categorization."""
        tracker = ShippingTracker()
        
        assert tracker._categorize_delay(0) == "on_time"
        assert tracker._categorize_delay(-1) == "on_time"
        assert tracker._categorize_delay(1) == "minor_delay"
        assert tracker._categorize_delay(5) == "moderate_delay"
        assert tracker._categorize_delay(10) == "major_delay"
    
    def test_rate_performance(self):
        """Test performance rating."""
        tracker = ShippingTracker()
        
        assert tracker._rate_performance(19, 20) == "excellent"  # 95%
        assert tracker._rate_performance(17, 20) == "good"       # 85%
        assert tracker._rate_performance(14, 20) == "fair"       # 70%
        assert tracker._rate_performance(10, 20) == "poor"       # 50%
    
    def test_assess_contract_compliance(self):
        """Test contract compliance assessment."""
        tracker = ShippingTracker()
        
        # Test compliant performance
        good_performance = {"on_time_percentage": 96}
        contract_terms = {"on_time_percentage": 95}
        
        compliance = tracker._assess_contract_compliance(good_performance, contract_terms)
        
        assert compliance["meets_sla"] == True
        assert compliance["breach_severity"] == "none"
        assert compliance["penalty_applicable"] == False
        
        # Test non-compliant performance
        poor_performance = {"on_time_percentage": 70}
        
        compliance = tracker._assess_contract_compliance(poor_performance, contract_terms)
        
        assert compliance["meets_sla"] == False
        assert compliance["breach_severity"] == "major"
        assert compliance["penalty_applicable"] == True
    
    @pytest.mark.asyncio
    async def test_analyze_shipping_disputes(self):
        """Test shipping disputes analysis."""
        tracker = ShippingTracker()
        
        # Mock track_shipment and verify_delivery methods
        tracker.track_shipment = AsyncMock(return_value={
            "tracking_number": "123456789012",
            "status": "delivered"
        })
        
        tracker.verify_delivery = AsyncMock(return_value={
            "delay_analysis": {
                "on_time": False,
                "delay_days": 3
            }
        })
        
        tracking_numbers = ["123456789012", "123456789013"]
        contract_terms = {"delivery_deadline": datetime.utcnow().isoformat()}
        
        result = await tracker.analyze_shipping_disputes(tracking_numbers, contract_terms)
        
        assert "total_shipments" in result
        assert "overall_performance" in result
        assert "contract_compliance" in result
        assert "recommendations" in result
        assert result["total_shipments"] == 2


if __name__ == "__main__":
    pytest.main([__file__])