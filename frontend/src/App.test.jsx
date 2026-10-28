import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

describe('Studio Split-Screen UI (App)', () => {
  beforeEach(() => {
    // Mock global fetch
    global.fetch = vi.fn().mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/accounts/status')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              tiktok: false,
              threads: true,
              facebook: false,
              youtube: false,
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    });

    // Mock global WebSocket
    class MockWebSocket {
      constructor(url) {
        this.url = url;
        this.onmessage = null;
        this.onopen = null;
        this.onclose = null;
        this.onerror = null;
      }
      close() {}
      send() {}
    }
    global.WebSocket = MockWebSocket;
  });

  it('renders header with app title and account connection badges', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText(/Social Video Publisher/i)).toBeInTheDocument();

    await waitFor(() => {
      const tiktokElements = screen.getAllByText(/TikTok/i);
      expect(tiktokElements.length).toBeGreaterThanOrEqual(1);

      const threadsElements = screen.getAllByText(/Threads/i);
      expect(threadsElements.length).toBeGreaterThanOrEqual(1);

      const facebookElements = screen.getAllByText(/Facebook/i);
      expect(facebookElements.length).toBeGreaterThanOrEqual(1);

      const youtubeElements = screen.getAllByText(/YouTube/i);
      expect(youtubeElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders left column with VideoUploadSection and AIPromptSection', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByRole('heading', { name: /Tải Video Lên/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Nhập ý tưởng \/ chủ đề video/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tạo Caption bằng AI/i })).toBeInTheDocument();
  });

  it('renders right column with 4 Platform Cards and publish button', async () => {
    await act(async () => {
      render(<App />);
    });
    // Check 4 platform cards exist
    expect(screen.getAllByRole('checkbox').length).toBeGreaterThanOrEqual(4);

    // Check Facebook specific options
    expect(screen.getByText(/Trang cá nhân \(Reel\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Fanpage/i)).toBeInTheDocument();

    // Check YouTube specific options
    expect(screen.getByPlaceholderText(/Tiêu đề YouTube Shorts/i)).toBeInTheDocument();

    // Check Publish button
    expect(screen.getByRole('button', { name: /Đăng Lên Tất Cả Nền Tảng Đã Chọn/i })).toBeInTheDocument();
  });

  it('renders live logs drawer', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText(/Nhật Ký Trực Tiếp \(Live Logs\)/i)).toBeInTheDocument();
  });
});
