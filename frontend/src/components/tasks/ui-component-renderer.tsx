// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Copy, Check, AlertTriangle } from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import type { UIComponent } from "@/types/task";

const CHART_COLORS = [
  "hsl(var(--primary))",
  "hsl(217, 91%, 60%)",
  "hsl(142, 71%, 45%)",
  "hsl(38, 92%, 50%)",
  "hsl(0, 84%, 60%)",
  "hsl(270, 70%, 60%)",
];

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 gap-1.5 text-xs"
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

function TableRenderer({ data }: { data: Record<string, unknown> }) {
  const headers = (data.headers as string[]) || [];
  const rows = (data.rows as unknown[][]) || [];
  const caption = data.caption as string | undefined;

  if (!headers.length) return null;

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        {caption && (
          <caption className="mt-2 text-xs text-muted-foreground">{caption}</caption>
        )}
        <TableHeader>
          <TableRow>
            {headers.map((h, i) => (
              <TableHead key={i}>{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {row.map((cell, j) => (
                <TableCell key={j}>{String(cell ?? "")}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function ChartRenderer({ data }: { data: Record<string, unknown> }) {
  const chartType = (data.chart_type as string) || "bar";
  const labels = (data.labels as string[]) || [];
  const datasets = (data.datasets as { label: string; values: number[] }[]) || [];

  if (!labels.length || !datasets.length) return null;

  // Transform to recharts format
  const chartData = labels.map((label, i) => {
    const point: Record<string, unknown> = { name: label };
    datasets.forEach((ds) => {
      point[ds.label] = ds.values[i] ?? 0;
    });
    return point;
  });

  const dataKeys = datasets.map((ds) => ds.label);

  const commonProps = {
    data: chartData,
    margin: { top: 5, right: 20, left: 0, bottom: 5 },
  };

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {chartType === "line" ? (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip />
            <Legend />
            {dataKeys.map((key, i) => (
              <Line key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} />
            ))}
          </LineChart>
        ) : chartType === "area" ? (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip />
            <Legend />
            {dataKeys.map((key, i) => (
              <Area key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]} fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={0.2} />
            ))}
          </AreaChart>
        ) : chartType === "pie" ? (
          <PieChart>
            <Pie data={chartData} dataKey={dataKeys[0]} nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
              {chartData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        ) : (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip />
            <Legend />
            {dataKeys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function CodeBlockRenderer({ data }: { data: Record<string, unknown> }) {
  const code = (data.code as string) || "";
  const language = (data.language as string) || "";
  const filename = data.filename as string | undefined;

  return (
    <div className="rounded-md border bg-muted/50 overflow-hidden">
      {filename && (
        <div className="flex items-center justify-between border-b bg-muted px-3 py-1.5">
          <span className="text-xs font-mono text-muted-foreground">{filename}</span>
          <CopyBtn text={code} />
        </div>
      )}
      <div className="relative">
        {!filename && (
          <div className="absolute right-2 top-2">
            <CopyBtn text={code} />
          </div>
        )}
        <pre className="overflow-x-auto p-3 text-sm">
          <code className={language ? `language-${language}` : ""}>{code}</code>
        </pre>
      </div>
      {language && (
        <div className="border-t px-3 py-1 text-[10px] text-muted-foreground">{language}</div>
      )}
    </div>
  );
}

function DiffRenderer({ data }: { data: Record<string, unknown> }) {
  const before = ((data.before as string) || "").split("\n");
  const after = ((data.after as string) || "").split("\n");

  return (
    <div className="rounded-md border overflow-hidden text-xs font-mono">
      <div className="grid grid-cols-2 divide-x">
        <div className="bg-red-500/5 p-2">
          <div className="mb-1 text-[10px] font-semibold text-red-400">Before</div>
          {before.map((line, i) => (
            <div key={i} className="text-red-400/80 whitespace-pre">{line}</div>
          ))}
        </div>
        <div className="bg-green-500/5 p-2">
          <div className="mb-1 text-[10px] font-semibold text-green-400">After</div>
          {after.map((line, i) => (
            <div key={i} className="text-green-400/80 whitespace-pre">{line}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ImageRenderer({ data }: { data: Record<string, unknown> }) {
  const url = data.url as string;
  const alt = (data.alt as string) || "Agent output";

  if (!url || !url.startsWith("https://")) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <AlertTriangle className="h-3.5 w-3.5" />
        Image blocked — HTTPS URLs only
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={alt}
      className="max-h-96 rounded-md border object-contain"
    />
  );
}

/**
 * Renders a single A2UI component based on its type.
 * Falls back to JSON display for unknown types.
 */
export function UIComponentRenderer({ component }: { component: UIComponent }) {
  const { type, title, data } = component;

  return (
    <div className="space-y-1.5">
      {title && <div className="text-sm font-medium">{title}</div>}
      {type === "table" && <TableRenderer data={data} />}
      {type === "chart" && <ChartRenderer data={data} />}
      {type === "code_block" && <CodeBlockRenderer data={data} />}
      {type === "diff" && <DiffRenderer data={data} />}
      {type === "image" && <ImageRenderer data={data} />}
      {!["table", "chart", "code_block", "diff", "image", "form", "calendar"].includes(type) && (
        <div className="rounded-md border bg-muted/50 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <AlertTriangle className="h-3 w-3" />
            Unknown component type: {type}
          </div>
          <pre className="overflow-auto text-xs">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
