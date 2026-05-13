.PHONY: start stop restart logs status url

start:   ## 启动 Duck Chat + Cloudflare 隧道（获取手机访问链接）
	bash start-duck.sh

stop:    ## 停止 Duck Chat + Cloudflare 隧道
	@if [ -f /tmp/duck-tunnel.pid ]; then \
		kill $$(cat /tmp/duck-tunnel.pid) 2>/dev/null || true; \
		rm -f /tmp/duck-tunnel.pid; \
		echo "☁️  隧道已停止"; \
	fi
	docker compose down
	@echo "✅ Duck Chat 已停止"

restart: ## 重启所有
	@$(MAKE) stop
	@$(MAKE) start

logs:    ## 查看日志
	docker compose logs -f

status:  ## 查看状态
	@docker compose ps 2>/dev/null; \
	echo "---"; \
	if [ -f /tmp/duck-tunnel.pid ] && kill -0 $$(cat /tmp/duck-tunnel.pid) 2>/dev/null; then \
		echo "☁️  隧道运行中"; \
		cat /tmp/duck-tunnel-history.log 2>/dev/null | tail -1; \
	else \
		echo "☁️  隧道未运行"; \
	fi

url:     ## 显示上次的隧道地址
	@if [ -f /tmp/duck-tunnel-history.log ]; then \
		echo "📋 隧道历史记录:"; \
		cat /tmp/duck-tunnel-history.log; \
	else \
		echo "暂无历史记录"; \
	fi
	@echo "💡 运行 'make start' 获取新的隧道地址"
