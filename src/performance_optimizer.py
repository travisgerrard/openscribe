# performance_optimizer.py
# Centralized performance optimization and monitoring

import time
import threading
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
try:
    from src.utils.utils import log_text
except ImportError:
    # Fallback for when running tests
    def log_text(category, message):
        print(f"[{category}] {message}")

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    component: str
    operation: str
    duration_ms: float
    timestamp: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    extra_data: Optional[Dict] = None

class PerformanceOptimizer:
    """Centralized performance optimization and monitoring system."""
    
    def __init__(self):
        self._metrics_history: List[PerformanceMetrics] = []
        self._thresholds = {
            'audio_processing_ms': 100,  # Audio processing should be under 100ms
            'vad_processing_ms': 10,     # VAD should be under 10ms
            'transcription_ms': 5000,    # Transcription should be under 5s
            'ui_update_ms': 16,          # UI updates should be under 16ms (60fps)
            'memory_growth_mb': 50,      # Memory growth alerts over 50MB
        }
        self._optimization_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
        # Performance tracking
        self._operation_start_times: Dict[str, float] = {}
        self._recent_metrics: Dict[str, List[float]] = {}
        
    def register_optimization_callback(self, metric_type: str, callback: Callable):
        """Register a callback to be called when optimization is needed."""
        self._optimization_callbacks[metric_type] = callback
        
    def start_operation(self, component: str, operation: str) -> str:
        """Start timing an operation. Returns operation ID."""
        operation_id = f"{component}:{operation}:{time.time()}"
        self._operation_start_times[operation_id] = time.time()
        return operation_id
        
    def end_operation(self, operation_id: str, extra_data: Optional[Dict] = None):
        """End timing an operation and record metrics."""
        if operation_id not in self._operation_start_times:
            return
            
        start_time = self._operation_start_times.pop(operation_id)
        duration_ms = (time.time() - start_time) * 1000
        
        # Parse operation details
        parts = operation_id.split(':')
        if len(parts) >= 2:
            component = parts[0]
            operation = parts[1]
        else:
            component = "unknown"
            operation = operation_id
            
        metric = PerformanceMetrics(
            component=component,
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            extra_data=extra_data
        )
        
        self._record_metric(metric)
        
    def _record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric and check for optimization opportunities."""
        with self._lock:
            self._metrics_history.append(metric)
            
            # Keep only recent metrics (last 1000)
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-1000:]
                
            # Track recent performance for trend analysis
            metric_key = f"{metric.component}_{metric.operation}_ms"
            if metric_key not in self._recent_metrics:
                self._recent_metrics[metric_key] = []
                
            self._recent_metrics[metric_key].append(metric.duration_ms)
            if len(self._recent_metrics[metric_key]) > 50:
                self._recent_metrics[metric_key] = self._recent_metrics[metric_key][-50:]
                
            # Check for performance issues
            self._check_performance_thresholds(metric, metric_key)
            
    def _check_performance_thresholds(self, metric: PerformanceMetrics, metric_key: str):
        """Check if performance metrics exceed thresholds and trigger optimizations."""
        threshold_key = f"{metric.operation}_ms"
        
        if threshold_key in self._thresholds:
            threshold = self._thresholds[threshold_key]
            
            if metric.duration_ms > threshold:
                log_text("PERF_WARN", 
                        f"{metric.component}.{metric.operation} took {metric.duration_ms:.1f}ms "
                        f"(threshold: {threshold}ms)")
                
                # Check if this is a consistent issue
                if metric_key in self._recent_metrics and len(self._recent_metrics[metric_key]) >= 5:
                    recent_avg = statistics.mean(self._recent_metrics[metric_key][-5:])
                    if recent_avg > threshold * 0.8:  # 80% of threshold consistently
                        self._trigger_optimization(metric.component, metric.operation, recent_avg)
                        
    def _trigger_optimization(self, component: str, operation: str, avg_duration: float):
        """Trigger automatic optimization for a component/operation."""
        callback_key = f"{component}_{operation}"
        
        if callback_key in self._optimization_callbacks:
            try:
                log_text("PERF_OPT", f"Triggering optimization for {component}.{operation} "
                                   f"(avg duration: {avg_duration:.1f}ms)")
                self._optimization_callbacks[callback_key]()
            except Exception as e:
                log_text("PERF_ERROR", f"Optimization callback failed for {callback_key}: {e}")
                
    def get_performance_summary(self) -> Dict:
        """Get a summary of recent performance metrics."""
        with self._lock:
            if not self._recent_metrics:
                return {}
                
            summary = {}
            for metric_key, values in self._recent_metrics.items():
                if values:
                    summary[metric_key] = {
                        'avg': statistics.mean(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values),
                        'recent_trend': 'improving' if len(values) >= 10 and 
                                      statistics.mean(values[-5:]) < statistics.mean(values[:5])
                                      else 'stable'
                    }
            return summary
            
    def optimize_audio_processing(self):
        """Optimization callback for audio processing performance issues."""
        log_text("PERF_OPT", "Optimizing audio processing: reducing buffer sizes and VAD frequency")
        # This would be called automatically when audio processing is too slow
        
    def optimize_ui_updates(self):
        """Optimization callback for UI update performance issues.""" 
        log_text("PERF_OPT", "Optimizing UI updates: increasing throttling and reducing DOM updates")
        # This would be called automatically when UI updates are too slow

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

# Convenience functions
def start_perf_timer(component: str, operation: str) -> str:
    """Start a performance timer. Returns operation ID."""
    return performance_optimizer.start_operation(component, operation)
    
def end_perf_timer(operation_id: str, extra_data: Optional[Dict] = None):
    """End a performance timer."""
    performance_optimizer.end_operation(operation_id, extra_data)
    
def get_perf_summary() -> Dict:
    """Get performance summary."""
    return performance_optimizer.get_performance_summary() 