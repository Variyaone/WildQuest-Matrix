"""
WildQuest Matrix - 稳定性优化模块

针对个人用户的稳定性优化：
1. 智能重试机制（自动重试失败的 API 调用）
2. 断点续传（支持从失败处恢复）
3. 容错执行（非必需步骤失败不中断）

Author: Variya
Version: 1.0.0
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import time


class RetryManager:
    """智能重试管理器"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_backoff: bool = True
    ):
        """
        初始化重试管理器

        Args:
            max_attempts: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_backoff: 是否使用指数退避
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff

    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数调用

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试次数用尽后抛出最后的异常
        """
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                print(f"尝试 {attempt}/{self.max_attempts} 失败: {e}")

                if attempt < self.max_attempts:
                    # 计算延迟时间
                    if self.exponential_backoff:
                        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                    else:
                        delay = self.base_delay

                    print(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)

        # 重试次数用尽，抛出最后的异常
        raise last_exception

    def retry_decorator(self, exceptions: tuple = (Exception,)):
        """
        重试装饰器

        Args:
            exceptions: 需要重试的异常类型

        Returns:
            装饰器函数
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.retry(func, *args, **kwargs)
            return wrapper
        return decorator


class CheckpointManager:
    """断点续传管理器"""

    def __init__(self, checkpoint_dir: str = "./checkpoints", retention_days: int = 7):
        """
        初始化检查点管理器

        Args:
            checkpoint_dir: 检查点目录
            retention_days: 检查点保留天数
        """
        self.checkpoint_dir = checkpoint_dir
        self.retention_days = retention_days
        os.makedirs(checkpoint_dir, exist_ok=True)

    def _get_checkpoint_file(self, step_id: int, date: Optional[datetime] = None) -> str:
        """
        获取检查点文件路径

        Args:
            step_id: 步骤 ID
            date: 日期，默认为今天

        Returns:
            检查点文件路径
        """
        if date is None:
            date = datetime.now()
        date_str = date.strftime('%Y%m%d')
        return os.path.join(self.checkpoint_dir, f"step_{step_id}_{date_str}.json")

    def save(self, step_id: int, data: Dict[str, Any]) -> str:
        """
        保存检查点

        Args:
            step_id: 步骤 ID
            data: 要保存的数据

        Returns:
            检查点文件路径
        """
        checkpoint_file = self._get_checkpoint_file(step_id)

        # 添加元数据
        checkpoint_data = {
            'step_id': step_id,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"检查点已保存: {checkpoint_file}")
        return checkpoint_file

    def load(self, step_id: int, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        加载检查点

        Args:
            step_id: 步骤 ID
            date: 日期，默认为今天

        Returns:
            检查点数据，如果不存在返回 None
        """
        checkpoint_file = self._get_checkpoint_file(step_id, date)

        if not os.path.exists(checkpoint_file):
            return None

        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)

        print(f"检查点已加载: {checkpoint_file}")
        return checkpoint_data.get('data')

    def exists(self, step_id: int, date: Optional[datetime] = None) -> bool:
        """
        检查检查点是否存在

        Args:
            step_id: 步骤 ID
            date: 日期，默认为今天

        Returns:
            检查点是否存在
        """
        checkpoint_file = self._get_checkpoint_file(step_id, date)
        return os.path.exists(checkpoint_file)

    def clear_old_checkpoints(self) -> int:
        """
        清理旧的检查点

        Returns:
            清理的文件数量
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cleared_count = 0

        for filename in os.listdir(self.checkpoint_dir):
            filepath = os.path.join(self.checkpoint_dir, filename)

            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_mtime < cutoff:
                    os.remove(filepath)
                    print(f"清理旧检查点: {filename}")
                    cleared_count += 1

        print(f"清理了 {cleared_count} 个旧检查点")
        return cleared_count

    def clear_all_checkpoints(self) -> int:
        """
        清理所有检查点

        Returns:
            清理的文件数量
        """
        cleared_count = 0

        for filename in os.listdir(self.checkpoint_dir):
            filepath = os.path.join(self.checkpoint_dir, filename)

            if os.path.isfile(filepath):
                os.remove(filepath)
                print(f"清理检查点: {filename}")
                cleared_count += 1

        print(f"清理了 {cleared_count} 个检查点")
        return cleared_count


class FaultTolerantPipeline:
    """容错管线执行器"""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        """
        初始化容错管线

        Args:
            checkpoint_manager: 检查点管理器，如果为 None 则创建新的
        """
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

    def execute_step(
        self,
        step_id: int,
        step_name: str,
        execute_func: Callable,
        required: bool = True,
        use_checkpoint: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step_id: 步骤 ID
            step_name: 步骤名称
            execute_func: 执行函数
            required: 是否必需步骤
            use_checkpoint: 是否使用检查点
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        start_time = datetime.now()

        # 尝试从检查点加载
        if use_checkpoint and self.checkpoint_manager.exists(step_id):
            print(f"步骤 {step_id} ({step_name}): 发现检查点，尝试恢复...")
            checkpoint_data = self.checkpoint_manager.load(step_id)

            if checkpoint_data:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                return {
                    'step_id': step_id,
                    'step_name': step_name,
                    'status': 'recovered',
                    'duration': duration,
                    'data': checkpoint_data,
                    'from_checkpoint': True
                }

        # 执行步骤
        try:
            print(f"步骤 {step_id} ({step_name}): 开始执行...")
            result = execute_func(**kwargs)

            # 保存检查点
            if use_checkpoint:
                self.checkpoint_manager.save(step_id, result)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                'step_id': step_id,
                'step_name': step_name,
                'status': 'success',
                'duration': duration,
                'data': result,
                'from_checkpoint': False
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            error_result = {
                'step_id': step_id,
                'step_name': step_name,
                'status': 'failed',
                'duration': duration,
                'error': str(e),
                'error_type': type(e).__name__,
                'from_checkpoint': False
            }

            print(f"步骤 {step_id} ({step_name}) 执行失败: {e}")

            # 如果是必需步骤，抛出异常
            if required:
                raise RuntimeError(f"必需步骤 {step_name} 执行失败") from e

            return error_result

    def execute_pipeline(
        self,
        steps: List[Dict[str, Any]],
        stop_on_first_failure: bool = False
    ) -> Dict[str, Any]:
        """
        执行管线

        Args:
            steps: 步骤列表，每个步骤包含:
                - id: 步骤 ID
                - name: 步骤名称
                - func: 执行函数
                - required: 是否必需（默认 True）
                - use_checkpoint: 是否使用检查点（默认 True）
                - kwargs: 其他参数
            stop_on_first_failure: 是否在第一次失败时停止

        Returns:
            管线执行结果
        """
        start_time = datetime.now()

        results = []
        failed_steps = []
        success_count = 0

        print(f"开始执行管线，共 {len(steps)} 个步骤...")
        print("=" * 60)

        for step in steps:
            step_id = step['id']
            step_name = step['name']
            execute_func = step['func']
            required = step.get('required', True)
            use_checkpoint = step.get('use_checkpoint', True)
            step_kwargs = step.get('kwargs', {})

            try:
                result = self.execute_step(
                    step_id=step_id,
                    step_name=step_name,
                    execute_func=execute_func,
                    required=required,
                    use_checkpoint=use_checkpoint,
                    **step_kwargs
                )

                results.append(result)

                if result['status'] in ['success', 'recovered']:
                    success_count += 1
                    print(f"✓ 步骤 {step_id} ({step_name}) 完成，耗时 {result['duration']:.2f} 秒")
                else:
                    failed_steps.append(result)
                    print(f"✗ 步骤 {step_id} ({step_name}) 失败")

                    if stop_on_first_failure:
                        print("停止执行管线")
                        break

            except Exception as e:
                print(f"步骤 {step_id} ({step_name}) 执行异常: {e}")
                failed_steps.append({
                    'step_id': step_id,
                    'step_name': step_name,
                    'status': 'failed',
                    'error': str(e)
                })

                if required:
                    print("必需步骤失败，停止执行管线")
                    break

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        print("=" * 60)
        print(f"管线执行完成: 成功 {success_count}/{len(steps)}，总耗时 {total_duration:.2f} 秒")

        return {
            'start_time': start_time,
            'end_time': end_time,
            'total_duration': total_duration,
            'total_steps': len(steps),
            'success_count': success_count,
            'failed_count': len(failed_steps),
            'success_rate': success_count / len(steps) if steps else 0,
            'results': results,
            'failed_steps': failed_steps,
            'success': len(failed_steps) == 0
        }


def resilient_api_call(
    url: str,
    params: Optional[Dict] = None,
    timeout: int = 30,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    弹性 API 调用（示例）

    Args:
        url: API URL
        params: 请求参数
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    Returns:
        API 响应数据

    Raises:
        Exception: 重试次数用尽后抛出异常
    """
    import requests

    retry_manager = RetryManager(
        max_attempts=max_retries,
        base_delay=1.0,
        max_delay=10.0,
        exponential_backoff=True
    )

    def _call():
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    return retry_manager.retry(_call)


if __name__ == "__main__":
    # 测试代码
    print("稳定性优化模块测试")

    # 测试重试管理器
    retry_manager = RetryManager(max_attempts=3)
    print(f"重试管理器: 最大尝试 {retry_manager.max_attempts} 次")

    # 测试检查点管理器
    checkpoint_manager = CheckpointManager(checkpoint_dir="./test_checkpoints")
    print(f"检查点管理器: 目录 {checkpoint_manager.checkpoint_dir}")

    # 测试保存和加载
    test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
    checkpoint_manager.save(1, test_data)
    loaded_data = checkpoint_manager.load(1)
    print(f"检查点测试: 保存和加载 {'成功' if loaded_data else '失败'}")

    # 清理测试检查点
    checkpoint_manager.clear_all_checkpoints()
