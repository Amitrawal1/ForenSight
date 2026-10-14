from PIL import Image

from app.pipeline.detectors.base import MediaContext
from app.pipeline.detectors.metadata.detector import MetadataDetector
from tests.helpers import jpeg_bytes, photo_like


def run(tmp_path, data, mime="image/jpeg"):
    p = tmp_path / "f"
    p.write_bytes(data)
    return MetadataDetector().run(MediaContext(p, "image", mime, tmp_path))


def test_no_metadata_is_informational_only(tmp_path):
    r = run(tmp_path, jpeg_bytes(photo_like()))
    assert r.reliability == 0.0


def test_editor_software_flags_manipulated(tmp_path):
    exif = Image.Exif()
    exif[0x0131] = "Adobe Photoshop 25.0"
    r = run(tmp_path, jpeg_bytes(photo_like(), exif=exif))
    assert r.fake_kind == "manipulated" and r.fake_score > 0.5
    assert "Photoshop" in r.reasons[0]


def test_camera_info_leans_authentic(tmp_path):
    exif = Image.Exif()
    exif[0x010F] = "Canon"
    exif[0x0110] = "Canon EOS R5"
    r = run(tmp_path, jpeg_bytes(photo_like(), exif=exif))
    assert r.fake_score < 0.5
    assert "Canon EOS R5" in r.reasons[0]


def test_iptc_ai_marker(tmp_path):
    xmp = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:Description '
           b'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/>'
           b"</x:xmpmeta>")
    r = run(tmp_path, jpeg_bytes(photo_like()) + xmp)
    assert r.fake_kind == "ai_generated" and r.fake_score > 0.9
