/** 模型配置页（M9-5，M8-3 前端接线）：列表 + 切换激活 + 新增（先 test 后保存）。
 *
 * - 列表展示 displayName/model/provider/apiKeyTail/isActive 高亮；
 * - 点击"启用" → PUT /models/{id}/activate；
 * - 新增表单：provider 下拉 + model + apiKey → 先 POST /models/test 验证 → 再 POST /models 保存；
 * - Key 只在表单临时存在，提交后清空；不显示明文，仅 apiKeyTail。
 */

import { useCallback, useEffect, useState } from "react";

import { activateModel, createModel, fetchModels, testModel } from "@/api/models";
import { PROVIDERS } from "@/api/types";
import type { ModelConfig, Provider } from "@/api/types";
import { Button } from "@/components/ui/button";

const PROVIDER_LABELS: Record<Provider, string> = {
  bailian: "百炼（阿里）",
  deepseek: "DeepSeek",
  openai: "OpenAI",
  anthropic: "Anthropic",
};

export default function ModelConfig() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 新增表单
  const [provider, setProvider] = useState<Provider>("bailian");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setModels(await fetchModels());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载模型配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleActivate = async (id: string) => {
    try {
      await activateModel(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "切换激活失败");
    }
  };

  const handleTestAndSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!model.trim() || !apiKey) {
      setFormError("请填写模型名与 API Key");
      return;
    }
    setTesting(true);
    try {
      // 先验证打通
      const test = await testModel(provider, apiKey, model);
      if (!test.ok) {
        setFormError(test.message || "Key 验证失败");
        return;
      }
      // 再保存
      await createModel(provider, apiKey, model);
      // 提交后清空表单（Key 不驻留）
      setModel("");
      setApiKey("");
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">模型配置</h1>
        <p className="mt-1 text-sm text-ink-500">
          配置 LLM Provider；API Key 仅加密存储，前端只显示尾号 4 位。
        </p>
      </div>

      {error && (
        <p className="rounded-md border border-risk-high/30 bg-[#FEF3F2] px-3 py-2 text-sm text-risk-highText">
          {error}
        </p>
      )}

      {/* 模型列表 */}
      <div className="overflow-hidden rounded-lg border border-line-200 bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line-200 bg-muted">
            <tr>
              <th className="px-4 py-3 font-medium text-ink-500">Provider</th>
              <th className="px-4 py-3 font-medium text-ink-500">模型名</th>
              <th className="px-4 py-3 font-medium text-ink-500">Key 尾号</th>
              <th className="px-4 py-3 font-medium text-ink-500">状态</th>
              <th className="px-4 py-3 font-medium text-ink-500">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-ink-400">
                  加载中…
                </td>
              </tr>
            )}
            {!loading && models.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-ink-400">
                  暂无模型配置，请新增
                </td>
              </tr>
            )}
            {!loading &&
              models.map((m) => (
                <tr key={m.id} className="border-b border-line-100 last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 text-ink-700">
                    {PROVIDER_LABELS[m.provider] ?? m.provider}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-700">{m.model}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-500">••••{m.apiKeyTail}</td>
                  <td className="px-4 py-3">
                    {m.isActive ? (
                      <span className="rounded-full bg-[#ECFDF3] px-2 py-0.5 text-xs font-medium text-risk-ok">
                        已激活
                      </span>
                    ) : (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-ink-400">
                        未激活
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {m.isActive ? (
                      <span className="text-xs text-ink-400">使用中</span>
                    ) : (
                      <button
                        onClick={() => handleActivate(m.id)}
                        className="text-sm font-medium text-brand-600 hover:text-brand-700"
                      >
                        启用
                      </button>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {/* 新增模型表单 */}
      <div className="rounded-lg border border-line-200 bg-surface p-5">
        <h2 className="text-base font-semibold text-ink-900">新增模型</h2>
        <form
          onSubmit={handleTestAndSave}
          className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as Provider)}
              className="h-9 w-full rounded-md border border-line-200 bg-surface px-2 text-sm focus:border-brand-600 focus:outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {PROVIDER_LABELS[p]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">模型名</label>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="如 qwen3.7-flash-2026-07-15"
              className="h-9 w-full rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-ink-600">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="输入 Key（加密存储，不显示明文）"
              className="h-9 w-full rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={testing} className="w-full">
              {testing ? "验证中…" : "验证并保存"}
            </Button>
          </div>
        </form>
        {formError && (
          <p className="mt-3 rounded-md border border-risk-high/30 bg-[#FEF3F2] px-3 py-2 text-xs text-risk-highText">
            {formError}
          </p>
        )}
      </div>
    </div>
  );
}
