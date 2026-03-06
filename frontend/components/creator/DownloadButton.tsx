'use client';

import { useState } from 'react';
import { Button, ButtonProps } from '@/components/ui/button';
import { Download, Loader2, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DownloadButtonProps extends Omit<ButtonProps, 'onClick'> {
  url: string;
  filename?: string;
  onDownloadStart?: () => void;
  onDownloadComplete?: () => void;
  onDownloadError?: (error: Error) => void;
}

export function DownloadButton({
  url,
  filename,
  onDownloadStart,
  onDownloadComplete,
  onDownloadError,
  children,
  className,
  size = 'default',
  variant = 'outline',
  ...props
}: DownloadButtonProps) {
  const [status, setStatus] = useState<'idle' | 'downloading' | 'complete' | 'error'>('idle');

  const handleDownload = async () => {
    if (status === 'downloading') return;

    setStatus('downloading');
    onDownloadStart?.();

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || getFilenameFromUrl(url);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setStatus('complete');
      onDownloadComplete?.();

      // Reset status after a short delay
      setTimeout(() => setStatus('idle'), 2000);
    } catch (error) {
      setStatus('error');
      onDownloadError?.(error instanceof Error ? error : new Error('Download failed'));

      // Reset status after a short delay
      setTimeout(() => setStatus('idle'), 2000);
    }
  };

  const getFilenameFromUrl = (url: string): string => {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      const segments = pathname.split('/');
      return segments[segments.length - 1] || 'download';
    } catch {
      return 'download';
    }
  };

  const getIcon = () => {
    switch (status) {
      case 'downloading':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'complete':
        return <Check className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Download className="h-4 w-4" />;
    }
  };

  const getLabel = () => {
    if (children) return children;

    switch (status) {
      case 'downloading':
        return 'Downloading...';
      case 'complete':
        return 'Downloaded!';
      case 'error':
        return 'Failed';
      default:
        return 'Download';
    }
  };

  return (
    <Button
      variant={status === 'error' ? 'destructive' : variant}
      size={size}
      className={cn('', className)}
      onClick={handleDownload}
      disabled={status === 'downloading'}
      {...props}
    >
      {getIcon()}
      {size !== 'icon' && <span className="ml-2">{getLabel()}</span>}
    </Button>
  );
}

interface DownloadAllButtonProps extends Omit<ButtonProps, 'onClick'> {
  urls: { url: string; filename?: string }[];
  onDownloadStart?: () => void;
  onDownloadComplete?: () => void;
  onDownloadError?: (error: Error) => void;
}

export function DownloadAllButton({
  urls,
  onDownloadStart,
  onDownloadComplete,
  onDownloadError,
  children,
  className,
  size = 'default',
  variant = 'outline',
  ...props
}: DownloadAllButtonProps) {
  const [status, setStatus] = useState<'idle' | 'downloading' | 'complete' | 'error'>('idle');
  const [progress, setProgress] = useState(0);

  const handleDownloadAll = async () => {
    if (status === 'downloading' || urls.length === 0) return;

    setStatus('downloading');
    setProgress(0);
    onDownloadStart?.();

    try {
      for (let i = 0; i < urls.length; i++) {
        const { url, filename } = urls[i];
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Download failed for ${filename || url}`);
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename || `download-${i + 1}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        setProgress(Math.round(((i + 1) / urls.length) * 100));

        // Small delay between downloads
        if (i < urls.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      }

      setStatus('complete');
      onDownloadComplete?.();

      setTimeout(() => {
        setStatus('idle');
        setProgress(0);
      }, 2000);
    } catch (error) {
      setStatus('error');
      onDownloadError?.(error instanceof Error ? error : new Error('Download failed'));

      setTimeout(() => {
        setStatus('idle');
        setProgress(0);
      }, 2000);
    }
  };

  const getIcon = () => {
    switch (status) {
      case 'downloading':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'complete':
        return <Check className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Download className="h-4 w-4" />;
    }
  };

  const getLabel = () => {
    if (children) return children;

    switch (status) {
      case 'downloading':
        return `Downloading... ${progress}%`;
      case 'complete':
        return 'Downloaded!';
      case 'error':
        return 'Failed';
      default:
        return `Download All (${urls.length})`;
    }
  };

  return (
    <Button
      variant={status === 'error' ? 'destructive' : variant}
      size={size}
      className={cn('', className)}
      onClick={handleDownloadAll}
      disabled={status === 'downloading' || urls.length === 0}
      {...props}
    >
      {getIcon()}
      {size !== 'icon' && <span className="ml-2">{getLabel()}</span>}
    </Button>
  );
}
