import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

// Mock Tauri core and event APIs
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(async (cmd: string) => {
    if (cmd === 'check_health') {
      return { status: 'healthy', version: '2026.03.01' };
    }
    if (cmd === 'get_capabilities') {
      return { ffmpeg_available: true, encoders: { audio: ['libmp3lame', 'aac'] } };
    }
    if (cmd === 'queue_list') {
      return [];
    }
    return {};
  }),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn(async () => () => {}),
}));

describe('MediaDock Frontend Application', () => {
  it('renders application navigation and branding title', async () => {
    render(<App />);
    expect(screen.getByText('MediaDock')).toBeDefined();
    expect(screen.getByText('Desktop Suite')).toBeDefined();
    expect(screen.getByText('Downloader')).toBeDefined();
    expect(screen.getByText('Download Queue')).toBeDefined();
    expect(screen.getByText('History')).toBeDefined();
    expect(screen.getByText('Settings')).toBeDefined();
    expect(screen.getByText('Diagnostics')).toBeDefined();
  });

  it('renders the URL input and analyze button', () => {
    render(<App />);
    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    expect(analyzeBtn).toBeDefined();
  });
});
