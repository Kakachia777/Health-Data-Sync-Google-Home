import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import redis
import hashlib
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class HealthTrend:
    metric_type: str
    trend: str
    change_percentage: float
    analysis: str

class DataAnalyzer:
    def __init__(self):
        self.trends_cache = {}
        
    @lru_cache(maxsize=100)
    def analyze_weight_trend(self, weight_data: List[Dict[str, Any]]) -> HealthTrend:
        """Analyze weight trends over time"""
        if not weight_data:
            return HealthTrend('weight', 'neutral', 0.0, 'Insufficient data')
            
        df = pd.DataFrame(weight_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        if len(df) < 2:
            return HealthTrend('weight', 'neutral', 0.0, 'Need more data points')
            
        # Calculate trend
        recent_avg = df['value'].tail(3).mean()
        past_avg = df['value'].head(3).mean()
        change = ((recent_avg - past_avg) / past_avg) * 100
        
        trend = 'increasing' if change > 1 else 'decreasing' if change < -1 else 'stable'
        analysis = f"Weight has {trend} by {abs(change):.1f}% over the period"
        
        return HealthTrend('weight', trend, change, analysis)
        
    def analyze_blood_pressure_trend(self, bp_data: List[Dict[str, Any]]) -> HealthTrend:
        """Analyze blood pressure trends"""
        if not bp_data:
            return HealthTrend('blood_pressure', 'neutral', 0.0, 'Insufficient data')
            
        df = pd.DataFrame(bp_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        if len(df) < 2:
            return HealthTrend('blood_pressure', 'neutral', 0.0, 'Need more data points')
            
        # Analyze systolic and diastolic separately
        systolic_data = [d['systolic'] for d in df['value']]
        diastolic_data = [d['diastolic'] for d in df['value']]
        
        sys_change = (np.mean(systolic_data[-3:]) - np.mean(systolic_data[:3]))
        dia_change = (np.mean(diastolic_data[-3:]) - np.mean(diastolic_data[:3]))
        
        if abs(sys_change) > 10 or abs(dia_change) > 10:
            trend = 'concerning'
        elif abs(sys_change) > 5 or abs(dia_change) > 5:
            trend = 'notable'
        else:
            trend = 'stable'
            
        analysis = f"BP trend: Systolic {sys_change:+.1f}, Diastolic {dia_change:+.1f}"
        return HealthTrend('blood_pressure', trend, max(abs(sys_change), abs(dia_change)), analysis)

class CacheManager:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url) if redis_url else None
        self.local_cache = {}
        
    def _generate_key(self, data: Dict[str, Any]) -> str:
        """Generate a unique cache key"""
        key_string = json.dumps(data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def get_cached_data(self, key_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        cache_key = self._generate_key(key_data)
        
        # Try Redis first
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
                
        # Fall back to local cache
        return self.local_cache.get(cache_key)
        
    def cache_data(self, key_data: Dict[str, Any], value: Dict[str, Any], 
                  expire_seconds: int = 3600) -> None:
        """Cache data with expiration"""
        cache_key = self._generate_key(key_data)
        
        # Cache in Redis if available
        if self.redis_client:
            self.redis_client.setex(
                cache_key,
                expire_seconds,
                json.dumps(value)
            )
            
        # Also cache locally
        self.local_cache[cache_key] = value

class HealthMetricsAggregator:
    def __init__(self):
        self.analyzer = DataAnalyzer()
        
    def generate_health_summary(self, 
                              weight_data: List[Dict[str, Any]],
                              bp_data: List[Dict[str, Any]],
                              hr_data: List[Dict[str, Any]],
                              sleep_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive health summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        # Analyze weight trends
        weight_trend = self.analyzer.analyze_weight_trend(weight_data)
        summary['metrics']['weight'] = {
            'trend': weight_trend.trend,
            'analysis': weight_trend.analysis,
            'latest': weight_data[-1]['value'] if weight_data else None
        }
        
        # Analyze blood pressure
        bp_trend = self.analyzer.analyze_blood_pressure_trend(bp_data)
        summary['metrics']['blood_pressure'] = {
            'trend': bp_trend.trend,
            'analysis': bp_trend.analysis,
            'latest': bp_data[-1]['value'] if bp_data else None
        }
        
        # Analyze heart rate variability
        if hr_data:
            hr_values = [d['value'] for d in hr_data]
            hr_variability = np.std(hr_values) if len(hr_values) > 1 else 0
            summary['metrics']['heart_rate'] = {
                'latest': hr_data[-1]['value'],
                'variability': hr_variability,
                'min': min(hr_values),
                'max': max(hr_values)
            }
            
        # Analyze sleep patterns
        if sleep_data:
            sleep_durations = []
            for sleep in sleep_data:
                start = datetime.fromisoformat(str(sleep['start']))
                end = datetime.fromisoformat(str(sleep['end']))
                duration = (end - start).total_seconds() / 3600  # hours
                sleep_durations.append(duration)
                
            summary['metrics']['sleep'] = {
                'average_duration': np.mean(sleep_durations),
                'quality': sleep_data[-1]['value'],
                'consistency': np.std(sleep_durations)
            }
            
        return summary

class NotificationManager:
    def __init__(self):
        self.alerts = []
        
    def check_health_metrics(self, summary: Dict[str, Any]) -> List[str]:
        """Check health metrics for concerning patterns"""
        alerts = []
        
        # Check blood pressure
        bp = summary['metrics'].get('blood_pressure', {})
        if bp.get('trend') == 'concerning':
            alerts.append(f"⚠️ Concerning blood pressure trend: {bp['analysis']}")
            
        # Check heart rate
        hr = summary['metrics'].get('heart_rate', {})
        if hr:
            if hr['max'] > 100:
                alerts.append(f"⚠️ High heart rate detected: {hr['max']} bpm")
            elif hr['variability'] > 20:
                alerts.append(f"ℹ️ High heart rate variability: {hr['variability']:.1f}")
                
        # Check sleep
        sleep = summary['metrics'].get('sleep', {})
        if sleep:
            if sleep['average_duration'] < 6:
                alerts.append(f"⚠️ Low sleep duration: {sleep['average_duration']:.1f} hours")
            if sleep['consistency'] > 2:
                alerts.append("ℹ️ Inconsistent sleep schedule detected")
                
        return alerts 