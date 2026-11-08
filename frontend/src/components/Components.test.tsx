import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueueTab } from './QueueTab';
import { DiagnosticsTab } from './DiagnosticsTab';
import { QueueItem, HealthStatus } from '../types';

describe('Frontend Modular Components', () => {
  it('renders QueueTab empty state and populated state', () => {
    const handleRefresh = vi.fn();
    const handlePause = vi.fn();
    const { rerender } = render(
      <QueueTab
        queueItems={[]}
        darkMode={true}
        onRefresh={handleRefresh}
        onPause={handlePause}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
        onRemove={vi.fn()}
        onReveal={vi.fn()}
      />
    );

    expect(screen.getByText('Download Queue Empty')).toBeDefined();

    const sampleItem: QueueItem = {
      id: 'job-123',
      url: 'https://example.com/video',
      title: 'Sample Test Video',
      state: 'downloading',
      percent: 45.5,
      downloaded_bytes: 4500000,
      total_bytes: 10000000,
      speed: 1048576,
      eta: 5,
      retry_count: 0,
      created_at: Date.now(),
    };

    rerender(
      <QueueTab
        queueItems={[sampleItem]}
        darkMode={true}
        onRefresh={handleRefresh}
        onPause={handlePause}
        onResume={vi.fn()}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
        onRemove={vi.fn()}
        onReveal={vi.fn()}
      />
    );

    expect(screen.getByText('Sample Test Video')).toBeDefined();
    expect(screen.getByText('45.5%')).toBeDefined();
    const pauseBtn = screen.getByTitle('Pause Download');
    fireEvent.click(pauseBtn);
    expect(handlePause).toHaveBeenCalledWith('job-123');
  });

  it('renders DiagnosticsTab with correct health status', () => {
    const health: HealthStatus = {
      status: 'healthy',
      dependencies: { ffmpeg: true, yt_dlp: true },
    };

    render(
      <DiagnosticsTab
        darkMode={true}
        health={health}
        capabilities={{
          ffmpeg: {
            version: '7.1',
            binary_path: '/usr/bin/ffmpeg',
            supported_audio_formats: ['mp3', 'aac'],
          },
        }}
        queueItems={[]}
        completedJobsCount={3}
      />
    );

    expect(screen.getByText('Python Engine Sidecar')).toBeDefined();
    expect(screen.getByText('Stdio JSON Lines')).toBeDefined();
    expect(screen.getByText('7.1')).toBeDefined();
  });
});
