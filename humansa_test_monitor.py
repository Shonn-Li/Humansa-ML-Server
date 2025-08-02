#!/usr/bin/env python3
"""
HUMANSA Test Monitor and Dashboard
==================================

Real-time monitoring and visualization of test execution.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import curses
from collections import deque, defaultdict
import threading

class TestMonitor:
    """Real-time test execution monitor"""
    
    def __init__(self, test_report_dir: str = "test_reports"):
        self.test_report_dir = Path(test_report_dir)
        self.current_tests = {}
        self.completed_tests = deque(maxlen=100)
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'in_progress': 0,
            'avg_response_time': 0.0,
            'by_category': defaultdict(lambda: {'total': 0, 'passed': 0})
        }
        self.running = False
        
    def start_test(self, test_id: str, test_name: str, category: str):
        """Record test start"""
        self.current_tests[test_id] = {
            'name': test_name,
            'category': category,
            'start_time': time.time(),
            'status': 'running'
        }
        self.stats['in_progress'] = len(self.current_tests)
        self.stats['total'] += 1
        
    def complete_test(self, test_id: str, success: bool, response_time: float):
        """Record test completion"""
        if test_id in self.current_tests:
            test_info = self.current_tests.pop(test_id)
            test_info['success'] = success
            test_info['response_time'] = response_time
            test_info['end_time'] = time.time()
            
            self.completed_tests.append(test_info)
            
            # Update stats
            if success:
                self.stats['passed'] += 1
                self.stats['by_category'][test_info['category']]['passed'] += 1
            else:
                self.stats['failed'] += 1
            
            self.stats['by_category'][test_info['category']]['total'] += 1
            self.stats['in_progress'] = len(self.current_tests)
            
            # Update average response time
            completed_count = self.stats['passed'] + self.stats['failed']
            if completed_count > 0:
                current_avg = self.stats['avg_response_time']
                self.stats['avg_response_time'] = (
                    (current_avg * (completed_count - 1) + response_time) / completed_count
                )
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        stats = self.stats.copy()
        stats['success_rate'] = (
            f"{(stats['passed'] / stats['total'] * 100):.2f}%" 
            if stats['total'] > 0 else "0%"
        )
        return stats
    
    def get_recent_tests(self, count: int = 10) -> List[Dict]:
        """Get recent test results"""
        return list(self.completed_tests)[-count:]


class TestDashboard:
    """Curses-based dashboard for test monitoring"""
    
    def __init__(self, monitor: TestMonitor):
        self.monitor = monitor
        self.screen = None
        self.running = False
        
    def run(self):
        """Run the dashboard"""
        try:
            curses.wrapper(self._run_dashboard)
        except KeyboardInterrupt:
            pass
    
    def _run_dashboard(self, stdscr):
        """Main dashboard loop"""
        self.screen = stdscr
        self.running = True
        
        # Setup colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Failure
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # In Progress
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Header
        
        # Configure screen
        self.screen.nodelay(True)
        curses.curs_set(0)
        
        while self.running:
            self._draw_dashboard()
            
            # Check for quit key
            key = self.screen.getch()
            if key == ord('q') or key == ord('Q'):
                self.running = False
            
            time.sleep(0.5)
    
    def _draw_dashboard(self):
        """Draw the dashboard"""
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        
        # Header
        header = "HUMANSA Test Monitor Dashboard (Press 'q' to quit)"
        self._draw_text(0, 0, header, curses.color_pair(4) | curses.A_BOLD)
        self._draw_text(1, 0, "=" * len(header), curses.color_pair(4))
        
        # Statistics
        stats = self.monitor.get_stats()
        row = 3
        
        self._draw_text(row, 0, "Overall Statistics:", curses.A_BOLD)
        row += 1
        
        self._draw_text(row, 2, f"Total Tests: {stats['total']}")
        row += 1
        
        self._draw_text(row, 2, f"Passed: {stats['passed']}", curses.color_pair(1))
        self._draw_text(row, 20, f"Failed: {stats['failed']}", curses.color_pair(2))
        self._draw_text(row, 38, f"In Progress: {stats['in_progress']}", curses.color_pair(3))
        row += 1
        
        self._draw_text(row, 2, f"Success Rate: {stats['success_rate']}")
        self._draw_text(row, 25, f"Avg Response: {stats['avg_response_time']:.2f}s")
        row += 2
        
        # Category breakdown
        self._draw_text(row, 0, "By Category:", curses.A_BOLD)
        row += 1
        
        for category, cat_stats in stats['by_category'].items():
            if cat_stats['total'] > 0:
                cat_success_rate = (cat_stats['passed'] / cat_stats['total'] * 100)
                self._draw_text(
                    row, 2, 
                    f"{category}: {cat_stats['passed']}/{cat_stats['total']} ({cat_success_rate:.1f}%)"
                )
                row += 1
        
        row += 1
        
        # Recent tests
        self._draw_text(row, 0, "Recent Tests:", curses.A_BOLD)
        row += 1
        
        recent_tests = self.monitor.get_recent_tests(10)
        for test in recent_tests:
            color = curses.color_pair(1) if test.get('success') else curses.color_pair(2)
            status = "PASS" if test.get('success') else "FAIL"
            self._draw_text(
                row, 2,
                f"[{status}] {test['name'][:40]:<40} {test['response_time']:.2f}s",
                color
            )
            row += 1
            
            if row >= height - 2:
                break
        
        # Current running tests
        if self.monitor.current_tests:
            row = min(row + 1, height - 10)
            self._draw_text(row, 0, "Running Tests:", curses.A_BOLD)
            row += 1
            
            for test_id, test_info in list(self.monitor.current_tests.items())[:5]:
                elapsed = time.time() - test_info['start_time']
                self._draw_text(
                    row, 2,
                    f"⟳ {test_info['name'][:40]:<40} {elapsed:.1f}s",
                    curses.color_pair(3)
                )
                row += 1
        
        self.screen.refresh()
    
    def _draw_text(self, row: int, col: int, text: str, attr=0):
        """Draw text at position with attributes"""
        try:
            self.screen.addstr(row, col, text, attr)
        except curses.error:
            pass  # Ignore if we try to write outside screen


class TestReportAnalyzer:
    """Analyze test reports and generate insights"""
    
    def __init__(self, report_dir: str = "test_reports"):
        self.report_dir = Path(report_dir)
    
    def analyze_latest_report(self) -> Dict:
        """Analyze the latest test report"""
        # Find latest summary report
        summary_files = list(self.report_dir.glob("*_summary.json"))
        if not summary_files:
            return {"error": "No test reports found"}
        
        latest_file = max(summary_files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            summary = json.load(f)
        
        # Load detailed report for deeper analysis
        detailed_file = latest_file.parent / latest_file.name.replace('_summary.json', '_detailed.json')
        if detailed_file.exists():
            with open(detailed_file, 'r') as f:
                detailed = json.load(f)
        else:
            detailed = []
        
        # Analyze patterns
        insights = {
            'report_name': summary['report_name'],
            'timestamp': summary['timestamp'],
            'overall_health': self._calculate_health_score(summary),
            'top_issues': self._identify_top_issues(detailed),
            'performance_insights': self._analyze_performance(summary, detailed),
            'recommendations': self._generate_recommendations(summary, detailed)
        }
        
        return insights
    
    def _calculate_health_score(self, summary: Dict) -> Dict:
        """Calculate overall system health score"""
        stats = summary['statistics']
        
        # Calculate scores
        execution_score = float(stats['execution_success_rate'].rstrip('%'))
        validation_score = float(stats['validation_success_rate'].rstrip('%'))
        
        # Performance score based on response times
        perf_stats = summary.get('performance', {})
        avg_time = perf_stats.get('avg_response_time', 10)
        performance_score = max(0, 100 - (avg_time - 5) * 10)  # Penalty for >5s
        
        # Overall health
        overall_score = (execution_score + validation_score + performance_score) / 3
        
        return {
            'overall_score': f"{overall_score:.1f}%",
            'execution_score': f"{execution_score:.1f}%",
            'validation_score': f"{validation_score:.1f}%",
            'performance_score': f"{performance_score:.1f}%",
            'grade': self._get_grade(overall_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _identify_top_issues(self, detailed: List[Dict]) -> List[Dict]:
        """Identify top issues from test results"""
        issue_counts = defaultdict(int)
        
        for test in detailed:
            validation = test.get('validation', {})
            for failure in validation.get('failures', []):
                # Categorize failure
                if 'Missing keywords:' in failure:
                    issue_counts['missing_keywords'] += 1
                elif 'Response time' in failure:
                    issue_counts['slow_response'] += 1
                elif 'Missing expected agents:' in failure:
                    issue_counts['missing_agents'] += 1
                elif 'too short:' in failure:
                    issue_counts['response_too_short'] += 1
                elif 'too long:' in failure:
                    issue_counts['response_too_long'] += 1
                else:
                    issue_counts['other'] += 1
        
        # Sort by frequency
        top_issues = [
            {'type': issue, 'count': count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        ][:5]
        
        return top_issues
    
    def _analyze_performance(self, summary: Dict, detailed: List[Dict]) -> Dict:
        """Analyze performance patterns"""
        perf_stats = summary.get('performance', {})
        
        # Find slowest categories
        category_perfs = []
        for cat, stats in summary.get('by_category', {}).items():
            # Find average response time for category
            cat_tests = [t for t in detailed if t['test_case']['category'] == cat]
            if cat_tests:
                avg_time = sum(
                    t['result']['response_time'] 
                    for t in cat_tests 
                    if t.get('result')
                ) / len(cat_tests)
                category_perfs.append({'category': cat, 'avg_time': avg_time})
        
        category_perfs.sort(key=lambda x: x['avg_time'], reverse=True)
        
        return {
            'avg_response_time': perf_stats.get('avg_response_time', 0),
            'p95_response_time': perf_stats.get('p95_response_time', 0),
            'slowest_categories': category_perfs[:3],
            'performance_grade': self._get_performance_grade(perf_stats.get('avg_response_time', 10))
        }
    
    def _get_performance_grade(self, avg_time: float) -> str:
        """Grade performance based on response time"""
        if avg_time < 2:
            return "Excellent"
        elif avg_time < 5:
            return "Good"
        elif avg_time < 10:
            return "Fair"
        elif avg_time < 15:
            return "Poor"
        else:
            return "Critical"
    
    def _generate_recommendations(self, summary: Dict, detailed: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        stats = summary['statistics']
        validation_rate = float(stats['validation_success_rate'].rstrip('%'))
        
        # Check validation rate
        if validation_rate < 80:
            recommendations.append(
                "Validation success rate is below 80%. Review failing test cases and update agent responses."
            )
        
        # Check performance
        perf = summary.get('performance', {})
        if perf.get('avg_response_time', 0) > 10:
            recommendations.append(
                "Average response time exceeds 10 seconds. Consider optimizing agent logic or adding caching."
            )
        
        # Check specific categories
        for cat, cat_stats in summary.get('by_category', {}).items():
            if cat_stats['total'] > 0:
                success_rate = (cat_stats['passed'] / cat_stats['total']) * 100
                if success_rate < 70:
                    recommendations.append(
                        f"{cat} category has low success rate ({success_rate:.1f}%). Focus testing on this area."
                    )
        
        # Check for missing agents
        issue_counts = {issue['type']: issue['count'] for issue in self._identify_top_issues(detailed)}
        if issue_counts.get('missing_agents', 0) > 10:
            recommendations.append(
                "Many tests report missing expected agents. Review agent routing logic."
            )
        
        if not recommendations:
            recommendations.append("System is performing well. Continue regular monitoring.")
        
        return recommendations


def demo_monitor():
    """Demo function to show monitor in action"""
    monitor = TestMonitor()
    dashboard = TestDashboard(monitor)
    
    # Simulate some test executions in background
    async def simulate_tests():
        categories = ["medical_consultation", "appointment", "product", "multi_turn"]
        test_id = 1
        
        while dashboard.running:
            # Start a test
            category = categories[test_id % len(categories)]
            monitor.start_test(f"test_{test_id}", f"Test Case {test_id}", category)
            
            # Simulate execution time
            await asyncio.sleep(2 + (test_id % 3))
            
            # Complete test
            success = test_id % 5 != 0  # Fail every 5th test
            response_time = 1.5 + (test_id % 4)
            monitor.complete_test(f"test_{test_id}", success, response_time)
            
            test_id += 1
            await asyncio.sleep(0.5)
    
    # Run simulation in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sim_task = loop.create_task(simulate_tests())
    
    # Run in thread
    def run_sim():
        loop.run_until_complete(sim_task)
    
    sim_thread = threading.Thread(target=run_sim)
    sim_thread.daemon = True
    sim_thread.start()
    
    # Run dashboard
    dashboard.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_monitor()
    else:
        # Analyze latest report
        analyzer = TestReportAnalyzer()
        insights = analyzer.analyze_latest_report()
        
        print("HUMANSA Test Report Analysis")
        print("=" * 50)
        print(f"Report: {insights.get('report_name', 'Unknown')}")
        print(f"Timestamp: {insights.get('timestamp', 'Unknown')}")
        print()
        
        health = insights.get('overall_health', {})
        print(f"Overall Health: {health.get('overall_score', 'N/A')} (Grade: {health.get('grade', 'N/A')})")
        print(f"  - Execution: {health.get('execution_score', 'N/A')}")
        print(f"  - Validation: {health.get('validation_score', 'N/A')}")
        print(f"  - Performance: {health.get('performance_score', 'N/A')}")
        print()
        
        print("Top Issues:")
        for issue in insights.get('top_issues', []):
            print(f"  - {issue['type']}: {issue['count']} occurrences")
        print()
        
        perf = insights.get('performance_insights', {})
        print(f"Performance: {perf.get('performance_grade', 'N/A')}")
        print(f"  - Avg Response: {perf.get('avg_response_time', 0):.2f}s")
        print(f"  - P95 Response: {perf.get('p95_response_time', 0):.2f}s")
        print()
        
        print("Recommendations:")
        for i, rec in enumerate(insights.get('recommendations', []), 1):
            print(f"  {i}. {rec}")