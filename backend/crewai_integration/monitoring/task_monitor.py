# backend/crewai_integration/monitoring/task_monitor.py
"""
任务监控和评估
"""
import logging
import time
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict
 
logger = logging.getLogger(__name__)
 
 
class TaskMonitor:
    """
    任务执行监控器
    
    功能：
    1. 记录任务执行时间
    2. 追踪任务成功/失败
    3. 收集性能指标
    4. 生成执行报告
    """
    
    def __init__(self):
        self.execution_id = None
        self.start_time = None
        self.tasks: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = defaultdict(list)
    
    def start_execution(self, ticker: str, query: str):
        """开始执行监控"""
        self.execution_id = f"{ticker}_{int(time.time())}"
        self.start_time = time.time()
        self.tasks = []
        self.metrics = defaultdict(list)
        
        logger.info(f"📊 Monitoring started: {self.execution_id}")
    
    def record_task_start(self, task_name: str, agent: str):
        """记录任务开始"""
        task_record = {
            "task_name": task_name,
            "agent": agent,
            "start_time": time.time(),
            "status": "running"
        }
        self.tasks.append(task_record)
        
        logger.info(f"▶️  Task started: {task_name} by {agent}")
    
    def record_task_completion(
        self,
        task_name: str,
        success: bool,
        duration: float = None,
        error: str = None
    ):
        """记录任务完成"""
        # 查找任务记录
        task_record = next(
            (t for t in self.tasks if t["task_name"] == task_name),
            None
        )
        
        if task_record:
            task_record["status"] = "success" if success else "failed"
            task_record["end_time"] = time.time()
            task_record["duration"] = duration or (
                task_record["end_time"] - task_record["start_time"]
            )
            if error:
                task_record["error"] = error
        else:
            # 创建新记录（如果没有start记录）
            task_record = {
                "task_name": task_name,
                "status": "success" if success else "failed",
                "duration": duration or 0,
                "end_time": time.time()
            }
            if error:
                task_record["error"] = error
            self.tasks.append(task_record)
        
        # 记录指标
        self.metrics["task_durations"].append(task_record["duration"])
        self.metrics["task_success"].append(success)
        
        status_emoji = "✅" if success else "❌"
        logger.info(
            f"{status_emoji} Task completed: {task_name} "
            f"({task_record['duration']:.2f}s)"
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        if not self.start_time:
            return {}
        
        total_time = time.time() - self.start_time
        total_tasks = len(self.tasks)
        successful_tasks = sum(
            1 for t in self.tasks if t.get("status") == "success"
        )
        failed_tasks = sum(
            1 for t in self.tasks if t.get("status") == "failed"
        )
        
        avg_task_duration = (
            sum(self.metrics["task_durations"]) / len(self.metrics["task_durations"])
            if self.metrics["task_durations"] else 0
        )
        
        return {
            "execution_id": self.execution_id,
            "total_execution_time": round(total_time, 2),
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": round(successful_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
            "average_task_duration": round(avg_task_duration, 2),
            "tasks": self.tasks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def print_report(self):
        """打印监控报告"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 CREWAI EXECUTION REPORT")
        print("="*60)
        print(f"Execution ID: {summary['execution_id']}")
        print(f"Total Time: {summary['total_execution_time']:.2f}s")
        print(f"Tasks: {summary['total_tasks']} total, "
              f"{summary['successful_tasks']} successful, "
              f"{summary['failed_tasks']} failed")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Avg Task Duration: {summary['average_task_duration']:.2f}s")
        print("-"*60)
        print("Task Details:")
        for task in summary['tasks']:
            status_emoji = "✅" if task.get("status") == "success" else "❌"
            print(f"  {status_emoji} {task['task_name']}: "
                  f"{task.get('duration', 0):.2f}s")
        print("="*60 + "\n")