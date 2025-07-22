"""
PerformanceTracker - Tracks and analyzes performance metrics over time
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time"""
    timestamp: datetime
    test_name: str
    success: bool
    attempts: int
    workflow_time: float = 0.0
    total_tokens: int = 0
    total_agents: int = 0
    iterations: int = 1
    total_events: int = 0
    errors: List[str] = field(default_factory=list)
    

class PerformanceTracker:
    """Tracks performance metrics and identifies trends"""
    
    def __init__(self):
        self.metrics_history: List[MetricSnapshot] = []
        self.test_success_rate: Dict[str, List[bool]] = defaultdict(list)
        self.performance_trends: Dict[str, List[float]] = defaultdict(list)
        self.agent_usage: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
    def record_result(self, result) -> None:
        """Record a test result"""
        snapshot = MetricSnapshot(
            timestamp=result.timestamp,
            test_name=result.test_name,
            success=result.success,
            attempts=result.attempts,
            workflow_time=result.metrics.get('workflow_time', 0.0),
            total_tokens=result.metrics.get('total_tokens', 0),
            total_agents=result.metrics.get('total_agents', 0),
            iterations=result.metrics.get('iterations', 1),
            total_events=result.metrics.get('total_events', 0),
            errors=result.errors
        )
        
        self.metrics_history.append(snapshot)
        
        # Track success rate
        self.test_success_rate[result.test_name].append(result.success)
        
        # Track performance metrics
        if result.success and snapshot.workflow_time > 0:
            self.performance_trends[result.test_name].append(snapshot.workflow_time)
            
        # Track errors
        for error in result.errors:
            self.error_patterns[self._categorize_error(error)] += 1
            
    def _categorize_error(self, error: str) -> str:
        """Categorize error messages"""
        error_lower = error.lower()
        
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower:
            return 'connection'
        elif 'validation' in error_lower:
            return 'validation'
        elif 'streaming' in error_lower:
            return 'streaming'
        elif 'citation' in error_lower:
            return 'citation'
        elif 'agent' in error_lower:
            return 'agent'
        else:
            return 'other'
            
    def calculate_success_rate(self, test_name: Optional[str] = None) -> float:
        """Calculate success rate for a specific test or overall"""
        if test_name:
            results = self.test_success_rate.get(test_name, [])
        else:
            results = [s for results in self.test_success_rate.values() for s in results]
            
        if not results:
            return 0.0
            
        return sum(results) / len(results) * 100
        
    def get_performance_trend(self, test_name: str) -> Dict[str, Any]:
        """Get performance trend for a specific test"""
        times = self.performance_trends.get(test_name, [])
        
        if not times:
            return {'status': 'no_data'}
            
        return {
            'status': 'available',
            'samples': len(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'min': min(times),
            'max': max(times),
            'trend': self._calculate_trend(times)
        }
        
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return 'insufficient_data'
            
        # Compare first half to second half
        mid = len(values) // 2
        first_half_avg = statistics.mean(values[:mid])
        second_half_avg = statistics.mean(values[mid:])
        
        diff_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if diff_percent < -10:
            return 'improving'  # Lower times = better
        elif diff_percent > 10:
            return 'degrading'
        else:
            return 'stable'
            
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get statistics about agent usage"""
        total_tests = len(self.metrics_history)
        
        agent_stats = {}
        for snapshot in self.metrics_history:
            if snapshot.total_agents > 0:
                # Track agent count distribution
                agent_count = snapshot.total_agents
                if agent_count not in agent_stats:
                    agent_stats[agent_count] = 0
                agent_stats[agent_count] += 1
                
        return {
            'total_tests': total_tests,
            'agent_distribution': agent_stats,
            'avg_agents_per_test': statistics.mean([s.total_agents for s in self.metrics_history])
            if self.metrics_history else 0
        }
        
    def identify_problem_areas(self) -> List[Dict[str, Any]]:
        """Identify tests or areas with problems"""
        problems = []
        
        # Find tests with low success rates
        for test_name, results in self.test_success_rate.items():
            success_rate = self.calculate_success_rate(test_name)
            if success_rate < 80:  # Less than 80% success
                problems.append({
                    'type': 'low_success_rate',
                    'test': test_name,
                    'success_rate': success_rate,
                    'total_runs': len(results),
                    'failures': results.count(False)
                })
                
        # Find tests with degrading performance
        for test_name, times in self.performance_trends.items():
            trend_info = self.get_performance_trend(test_name)
            if trend_info.get('trend') == 'degrading':
                problems.append({
                    'type': 'performance_degradation',
                    'test': test_name,
                    'trend': trend_info
                })
                
        # Find common error patterns
        for error_type, count in self.error_patterns.items():
            if count > 5:  # More than 5 occurrences
                problems.append({
                    'type': 'frequent_error',
                    'error_category': error_type,
                    'occurrences': count
                })
                
        return problems
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        total_tests = len(self.metrics_history)
        successful_tests = sum(1 for s in self.metrics_history if s.success)
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': total_tests - successful_tests,
                'overall_success_rate': f"{self.calculate_success_rate():.2f}%",
                'total_unique_tests': len(self.test_success_rate)
            },
            'performance': {
                'avg_workflow_time': statistics.mean([s.workflow_time for s in self.metrics_history if s.workflow_time > 0])
                if any(s.workflow_time > 0 for s in self.metrics_history) else 0,
                'avg_tokens_used': statistics.mean([s.total_tokens for s in self.metrics_history if s.total_tokens > 0])
                if any(s.total_tokens > 0 for s in self.metrics_history) else 0,
            },
            'test_specific': {},
            'error_patterns': dict(self.error_patterns),
            'problem_areas': self.identify_problem_areas(),
            'agent_statistics': self.get_agent_statistics()
        }
        
        # Add test-specific stats
        for test_name in self.test_success_rate:
            report['test_specific'][test_name] = {
                'success_rate': f"{self.calculate_success_rate(test_name):.2f}%",
                'runs': len(self.test_success_rate[test_name]),
                'performance_trend': self.get_performance_trend(test_name)
            }
            
        return report
        
    def export_metrics(self, filepath: str) -> None:
        """Export metrics to JSON file"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'metrics_history': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'test_name': s.test_name,
                    'success': s.success,
                    'attempts': s.attempts,
                    'workflow_time': s.workflow_time,
                    'total_tokens': s.total_tokens,
                    'total_agents': s.total_agents,
                    'iterations': s.iterations,
                    'total_events': s.total_events,
                    'errors': s.errors
                }
                for s in self.metrics_history
            ],
            'report': self.generate_report()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Metrics exported to: {filepath}")
        
    def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Generate suggestions for improvements based on metrics"""
        suggestions = []
        
        # Analyze problem areas
        problems = self.identify_problem_areas()
        
        for problem in problems:
            if problem['type'] == 'low_success_rate':
                suggestions.append({
                    'priority': 'high',
                    'type': 'fix_test',
                    'test': problem['test'],
                    'issue': f"Success rate only {problem['success_rate']:.1f}%",
                    'suggestion': 'Analyze failure patterns and implement targeted fixes'
                })
                
            elif problem['type'] == 'performance_degradation':
                suggestions.append({
                    'priority': 'medium',
                    'type': 'optimize',
                    'test': problem['test'],
                    'issue': 'Performance is degrading over time',
                    'suggestion': 'Profile the test to identify bottlenecks'
                })
                
            elif problem['type'] == 'frequent_error':
                suggestions.append({
                    'priority': 'high',
                    'type': 'fix_error',
                    'error': problem['error_category'],
                    'issue': f"{problem['occurrences']} occurrences",
                    'suggestion': f'Implement better {problem["error_category"]} handling'
                })
                
        return sorted(suggestions, key=lambda x: x['priority'] == 'high', reverse=True)