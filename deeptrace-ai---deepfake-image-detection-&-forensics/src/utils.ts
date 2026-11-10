import type { DetectionRecord } from './types';

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export function validateUpload(file: Pick<File, 'name' | 'size' | 'type'>): string | null {
  if (!/\.(jpe?g|png|webp)$/i.test(file.name)) return 'Choose a JPG, JPEG, PNG, or WEBP file.';
  if (file.type && !['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].includes(file.type.toLowerCase())) return 'The file type does not match a supported image format.';
  if (file.size === 0) return 'The selected file is empty.';
  if (file.size > MAX_UPLOAD_BYTES) return 'The image exceeds the 10 MB upload limit.';
  return null;
}
export function formatTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : 'Not returned by the server';
}
export function formatScore(value: number): string { return `${(value * 100).toFixed(1)}%`; }
export function csvCell(value: string | number): string {
  let text = String(value);
  // Quoting alone does not prevent spreadsheet formula execution.
  if (/^[\s]*[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}
export function historyCsv(records: DetectionRecord[]): string {
  const rows: (string | number)[][] = [['Record ID', 'Filename', 'Prediction', 'Model confidence score', 'Real score', 'Fake score', 'Real-score threshold', 'Processing Time (s)', 'Created at (UTC)']];
  records.forEach(record => rows.push([record.id, record.filename, record.prediction, record.confidence, record.real_probability, record.fake_probability, record.threshold ?? 'Unknown', record.processing_time, record.timestamp]));
  return '﻿' + rows.map(row => row.map(csvCell).join(',')).join('\r\n');
}
export function downloadFile(content: BlobPart, filename: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = filename;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function clampPage(page: number, count: number, size = 10): number {
  return Math.max(1, Math.min(page, Math.ceil(count / size) || 1));
}
