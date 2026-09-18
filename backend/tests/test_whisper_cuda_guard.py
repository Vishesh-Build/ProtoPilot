import unittest
from unittest import mock

from app.config import settings
from app.transcription import whisper_service


class WhisperCudaGuardTest(unittest.TestCase):
    def test_whisper_skips_cuda_download_when_no_gpu(self):
        # Force is_cuda_available to return False (as on Render CPU or laptop without Nvidia GPU)
        with mock.patch("app.transcription.whisper_service.is_cuda_available", return_value=False):
            with mock.patch("app.transcription.whisper_service.WhisperModel") as mock_whisper_model:
                mock_whisper_model.return_value = mock.MagicMock()
                model, device = whisper_service._load_model_blocking(force_cpu=False)

                # Should return cpu device
                self.assertEqual(device, "cpu")
                # WhisperModel should have been called with cpu fallback size (tiny), NOT medium
                self.assertEqual(mock_whisper_model.call_count, 1)
                called_model_size = mock_whisper_model.call_args[0][0]
                called_device = mock_whisper_model.call_args[1].get("device")
                self.assertEqual(called_device, "cpu")
                self.assertEqual(called_model_size, settings.whisper_cpu_fallback_model_size)
                self.assertEqual(called_model_size, "tiny")

    def test_whisper_uses_cuda_when_available(self):
        # When CUDA is present
        with mock.patch("app.transcription.whisper_service.is_cuda_available", return_value=True):
            with mock.patch("app.transcription.whisper_service.WhisperModel") as mock_whisper_model:
                with mock.patch("app.transcription.whisper_service._cuda_warmup_transcribe"):
                    mock_whisper_model.return_value = mock.MagicMock()
                    model, device = whisper_service._load_model_blocking(force_cpu=False)

                    self.assertEqual(device, "cuda")
                    called_model_size = mock_whisper_model.call_args[0][0]
                    called_device = mock_whisper_model.call_args[1].get("device")
                    self.assertEqual(called_device, "cuda")
                    self.assertEqual(called_model_size, settings.whisper_model_size)


if __name__ == "__main__":
    unittest.main()
