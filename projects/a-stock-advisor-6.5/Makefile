.PHONY: help install dev test lint format clean build publish docs data backup run

help:
	@echo "WildQuest Matrix - 构建命令"
	@echo ""
	@echo "安装命令:"
	@echo "  make install      安装生产依赖"
	@echo "  make dev          安装开发依赖"
	@echo "  make install-all  安装所有依赖（包括可选依赖）"
	@echo ""
	@echo "开发命令:"
	@echo "  make test         运行所有测试"
	@echo "  make test-cov     运行测试并生成覆盖率报告"
	@echo "  make lint         运行代码检查"
	@echo "  make format       格式化代码"
	@echo "  make typecheck    类型检查"
	@echo ""
	@echo "构建命令:"
	@echo "  make build        构建分发包"
	@echo "  make publish      发布到PyPI"
	@echo "  make clean        清理构建产物"
	@echo ""
	@echo "数据命令:"
	@echo "  make data-init    初始化数据目录"
	@echo "  make data-update  更新数据"
	@echo "  make backup       备份数据"
	@echo ""
	@echo "运行命令:"
	@echo "  make run          运行主程序"
	@echo "  make run-daily    运行每日任务"
	@echo "  make run-backtest 运行回测"

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e ".[dev]"

install-all:
	python3 -m pip install -e ".[all]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=core --cov-report=html --cov-report=term

test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

lint:
	flake8 core/ tests/
	isort --check-only core/ tests/
	black --check core/ tests/

format:
	isort core/ tests/
	black core/ tests/

typecheck:
	mypy core/

build: clean
	python3 -m build

publish: build
	twine upload dist/*

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

docs:
	cd docs && make html

data-init:
	python3 -c "from core.infrastructure.config import get_data_paths; get_data_paths()"

data-update:
	python3 -m core.data.scheduler

backup:
	python3 -m core.daily.backup

run:
	python3 -m core.main

run-daily:
	python3 -m core.daily.scheduler

run-backtest:
	python3 -m core.backtest.engine

pre-commit:
	pre-commit run --all-files

check: lint typecheck test
	@echo "所有检查通过！"
