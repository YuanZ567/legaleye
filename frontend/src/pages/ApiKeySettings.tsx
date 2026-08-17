/** API Key 设置页（M9-8，所有登录用户可见）：谁用谁付费。
 *
 * - 展示当前状态：已配置 → apiKeyTail（****abcd）+ 清除；未配置 → "未配置"；
 * - 输入 Key（password）+ 保存 → PUT /users/me/api-key → 显示尾号；
 * - 清除 → confirm → DELETE /users/me/api-key；
 * - 配置了自有 Key → 用户无限次；未配置 → 走系统 Key 但限 3 次/日（页面提示）。
 */

import { useEffect, useState } from "react";

import { getUser } from "@/api/client";
import { clearMyApiKey, setMyApiKey } from "@/api/userApiKey";
import type { User } from "@/api/types";
import { Button } from "@/components/ui/button";

export default function ApiKeySettings() {
  const [tail, setTail] = useState<string | null>(() => getUser<User>()?.apiKeyTail ?? null);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTail(getUser<User>()?.apiKeyTail ?? null);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!apiKey.trim()) {
      setError("请输入 API Key");
      return;
    }
    setSaving(true);
    try {
      const newTail = await setMyApiKey(apiKey.trim());
      setTail(newTail);
      setApiKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("确定清除你的 API Key？清除后将回到系统 Key 的 3 次/日限制。")) {
      return;
    }
    setError(null);
    try {
      await clearMyApiKey();
      setTail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "清除失败");
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">API Key 设置</h1>
        <p className="mt-1 text-sm text-ink-500">
          配置你自己的 LLM API Key：审查任务将用你的 Key 调用（谁用谁付费，无限次）；
          未配置则使用系统 Key，但每日限 3 次 demo 审查。
        </p>
      </div>

      {/* 当前状态 */}
      <div className="rounded-lg border border-line-200 bg-surface p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-ink-600">当前 API Key</div>
            <div className="mt-1 font-mono text-lg text-ink-900">
              {tail ? tail : <span className="text-ink-400">未配置</span>}
            </div>
            {tail ? (
              <p className="mt-1 text-xs text-risk-ok">已配置自有 Key，审查不受每日次数限制。</p>
            ) : (
              <p className="mt-1 text-xs text-ink-400">未配置：审查走系统 Key，每日限 3 次。</p>
            )}
          </div>
          {tail && (
            <Button variant="outline" onClick={handleClear}>
              清除
            </Button>
          )}
        </div>
      </div>

      {/* 设置表单 */}
      <form onSubmit={handleSave} className="rounded-lg border border-line-200 bg-surface p-5">
        <label className="mb-1 block text-xs font-medium text-ink-600">
          新的 API Key（百炼 DashScope 兼容 Key）
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="sk-..."
          className="h-9 w-full rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none"
        />
        {error && (
          <p className="mt-3 rounded-md border border-risk-high/30 bg-[#FEF3F2] px-3 py-2 text-xs text-risk-highText">
            {error}
          </p>
        )}
        <div className="mt-4 flex justify-end">
          <Button type="submit" disabled={saving || !apiKey.trim()}>
            {saving ? "保存中…" : "保存"}
          </Button>
        </div>
      </form>
    </div>
  );
}
