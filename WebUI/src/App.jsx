import React, { useState } from 'react';
import axios from 'axios';
import { Container, Card, Form, Button, Table, Modal, Spinner, Badge, Row, Col } from 'react-bootstrap';

const platformPatterns = {
  'Youtube': {
    placeholder: 'https://www.youtube.com/watch?v=<your_video_id>',
    regex: /youtube\.com\/watch\?v=/i,
    error: 'URL must be in the format: https://www.youtube.com/watch?v=...'
  },
  'Facebook': {
    placeholder: 'https://www.facebook.com/<your_page>/videos/<your_video_id>',
    regex: /facebook\.com\/.*\/videos\//i,
    error: 'URL must be in the format: https://www.facebook.com/<page>/videos/<id>'
  },
  'X': {
    placeholder: 'https://x.com/i/broadcasts/<your_video_id>',
    regex: /(x|twitter)\.com\/i\/broadcasts\//i,
    error: 'URL must be in the format: https://x.com/i/broadcasts/...'
  },
  'TikTok': {
    placeholder: '@streamer_name',
    regex: /^@?[\w.-]+$/,
    error: 'ชื่อ Creator ต้องเป็น Username (เช่น @streamer_name)'
  }
};

function App() {
  const [platform, setPlatform] = useState('');
  const [url, setUrl] = useState('');
  const [tiktokApiKey, setTiktokApiKey] = useState('');
  const [tiktokLimit, setTiktokLimit] = useState(50);

  const [loading, setLoading] = useState(false);
  const [currentData, setCurrentData] = useState(null);
  const [currentPlatform, setCurrentPlatform] = useState('');
  const [currentUrl, setCurrentUrl] = useState('');
  const [hasError, setHasError] = useState(false);
  
  const [showResults, setShowResults] = useState(false);
  
  const [alertModal, setAlertModal] = useState({ show: false, title: '', message: '' });
  const [apiGuideModal, setApiGuideModal] = useState(false);
  
  const [urlError, setUrlError] = useState('');

  const showAlert = (title, message) => {
    setAlertModal({ show: true, title, message });
  };

  const handlePlatformChange = (e) => {
    const p = e.target.value;
    setPlatform(p);
    setUrlError('');
  };

  const handleUrlChange = (e) => {
    setUrl(e.target.value);
    setUrlError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!platform) {
      setUrlError('กรุณาเลือกแพลตฟอร์ม');
      return;
    }

    const pattern = platformPatterns[platform].regex;
    if (!pattern.test(url)) {
      setUrlError(platformPatterns[platform].error);
      return;
    }

    setLoading(true);
    setShowResults(false);
    setCurrentData(null);
    setCurrentPlatform(platform);
    setCurrentUrl(url);
    setHasError(false);

    try {
      const apiUrl = import.meta.env.VITE_BACKEND_API || 'http://localhost:8000/api/v1/live';
      
      const params = { platform, url };
      if (platform === 'TikTok') {
        params.api_key = tiktokApiKey;
        params.limit = tiktokLimit;
      }

      const response = await axios.get(apiUrl, {
        params,
        headers: { 'Accept': 'application/json' }
      });

      const data = response.data;

      setCurrentData(data);
      setHasError(false);
      if (typeof data === 'object') {
        showAlert('สำเร็จ', 'ดึงข้อมูลสำเร็จแล้ว!');
      }
    } catch (error) {
      setHasError(true);
      setCurrentData(
        error.response?.data || error.message || 'An unexpected error occurred.'
      );
    } finally {
      setLoading(false);
      setShowResults(true);
    }
  };

  const getICTTimestamp = () => {
    return new Date().toLocaleString('en-GB', { timeZone: 'Asia/Bangkok' }).replace(',', '');
  };

  const escapeCSV = (str) => {
    if (str === null || str === undefined) return '';
    return String(str).replace(/,/g, ' ').replace(/\n/g, ' ').replace(/"/g, '');
  };

  const downloadCSV = (csv, filename) => {
    const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadSummary = () => {
    if (!currentData || typeof currentData !== 'object') return;

    const timestamp = getICTTimestamp();
    const platformStr = escapeCSV(currentPlatform);
    const urlStr = escapeCSV(currentUrl);
    const link = escapeCSV(currentData.url);
    const title = escapeCSV(currentData.title);
    const viewers = escapeCSV(currentData.viewers !== undefined ? currentData.viewers : '');
    const errorMsg = escapeCSV(currentData.error_message || 'No Error');

    const csvContent = `timestamp (ICT),platform,url,link,title,viewers,error message\n${timestamp},${platformStr},${urlStr},${link},${title},${viewers},${errorMsg}`;
    downloadCSV(csvContent, 'summary.csv');
    showAlert('สำเร็จ', 'บันทึกไฟล์ Summary CSV สำเร็จแล้ว!');
  };

  const handleDownloadChat = () => {
    if (!currentData || !currentData.chat_messages || !Array.isArray(currentData.chat_messages)) return;

    const timestamp = getICTTimestamp();
    const platformStr = escapeCSV(currentPlatform);
    const title = escapeCSV(currentData.title);
    const urlStr = escapeCSV(currentUrl);

    let csvContent = `id,timestamp,platform,title,url,sender,message\n`;
    currentData.chat_messages.forEach(chat => {
      const id = escapeCSV(chat.id);
      const sender = escapeCSV(chat.sender);
      const message = escapeCSV(chat.message);
      csvContent += `${id},${timestamp},${platformStr},${title},${urlStr},${sender},${message}\n`;
    });

    downloadCSV(csvContent, 'chat_messages.csv');
    showAlert('สำเร็จ', 'บันทึกไฟล์ Chat CSV สำเร็จแล้ว!');
  };

  const handleDownloadJson = () => {
    if (!currentData) return;

    const jsonContent = typeof currentData === 'object' ? JSON.stringify(currentData, null, 2) : currentData;
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement("a");
    const urlObj = URL.createObjectURL(blob);
    link.setAttribute("href", urlObj);
    link.setAttribute("download", 'response.json');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showAlert('สำเร็จ', 'บันทึกไฟล์ JSON สำเร็จแล้ว!');
  };

  const currentPattern = platformPatterns[platform];
  const placeholder = currentPattern ? currentPattern.placeholder : 'https://www.youtube.com/watch?v=...';
  const labelText = platform === 'TikTok' ? 'ชื่อ Creator' : 'ลิงก์ไลฟ์สด (URL)';

  return (
    <Container className="py-5" style={{ maxWidth: '900px' }}>
      <header className="text-center mb-5">
        <img src="/live.png" alt="Live Scraper" width="100" className="mb-3" />
        <h1 className="fw-bold d-flex align-items-center justify-content-center gap-3">
          <i className="bi bi-mortarboard-fill text-primary"></i> ระบบดูดข้อมูลไลฟ์สด
          <Badge bg="primary" pill style={{ fontSize: '0.9rem' }}>version 1</Badge>
        </h1>
        <p className="text-muted fs-5">ดึงข้อมูลชื่อไลฟ์ ยอดคนดู และข้อความคอมเมนต์จากไลฟ์สด</p>
      </header>

      <main>
        <Card className="shadow-sm mb-4 border-0">
          <Card.Body className="p-4">
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-4">
                <Form.Label className="fw-semibold">
                  <i className="bi bi-globe me-2"></i> แพลตฟอร์ม
                </Form.Label>
                <Form.Select required value={platform} onChange={handlePlatformChange} size="lg">
                  <option value="" disabled>เลือกแพลตฟอร์ม</option>
                  <option value="Youtube">YouTube</option>
                  <option value="Facebook">Facebook</option>
                  <option value="X">X (Twitter)</option>
                  <option value="TikTok">TikTok</option>
                </Form.Select>
              </Form.Group>

              <Form.Group className="mb-4">
                <Form.Label className="fw-semibold">
                  <i className={platform === 'TikTok' ? "bi bi-person-fill me-2" : "bi bi-record-circle-fill text-danger me-2"}></i> 
                  {labelText}
                </Form.Label>
                <Form.Control 
                  type="text" 
                  placeholder={placeholder} 
                  required 
                  value={url}
                  onChange={handleUrlChange}
                  isInvalid={!!urlError}
                  size="lg"
                />
                <Form.Control.Feedback type="invalid">
                  {urlError}
                </Form.Control.Feedback>
              </Form.Group>

              {platform === 'TikTok' && (
                <div className="mb-4 p-3 bg-light rounded">
                  <Form.Group className="mb-3">
                    <div className="d-flex justify-content-between align-items-baseline mb-2">
                      <Form.Label className="fw-semibold mb-0">
                        <i className="bi bi-key-fill me-2"></i> Tik Tools API Key
                      </Form.Label>
                      <a 
                        href="#" 
                        className="text-primary text-decoration-none small"
                        onClick={(e) => { e.preventDefault(); setApiGuideModal(true); }}
                      >
                        <i className="bi bi-question-circle me-1"></i>วิธีรับ API Key?
                      </a>
                    </div>
                    <Form.Control 
                      type="text" 
                      placeholder="tk_xxxxxxxxxx..." 
                      required 
                      value={tiktokApiKey}
                      onChange={(e) => setTiktokApiKey(e.target.value)}
                    />
                  </Form.Group>
                  <Form.Group>
                    <Form.Label className="fw-semibold">
                      <i className="bi bi-123 me-2"></i> จำนวนคอมเมนต์ที่ต้องการ
                    </Form.Label>
                    <Form.Control 
                      type="number" 
                      placeholder="50" 
                      min="1" 
                      value={tiktokLimit}
                      onChange={(e) => setTiktokLimit(parseInt(e.target.value) || 1)}
                    />
                  </Form.Group>
                </div>
              )}

              <Button type="submit" variant="primary" size="lg" className="w-100 fw-bold d-flex justify-content-center align-items-center gap-2" disabled={loading}>
                {loading ? (
                  <>
                    <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                    กำลังดึงข้อมูล...
                  </>
                ) : (
                  <>
                    <i className="bi bi-rocket-takeoff"></i> เริ่มดึงข้อมูล
                  </>
                )}
              </Button>
            </Form>
          </Card.Body>
        </Card>

        {showResults && (
          <div className="animate__animated animate__fadeInUp">
            <Row className="g-4">
              <Col md={12}>
                <Card className="shadow-sm border-0 h-100">
                  <Card.Header className="bg-white border-bottom d-flex justify-content-between align-items-center py-3">
                    <h5 className="mb-0 fw-bold text-primary">
                      <i className="bi bi-info-circle me-2"></i> 
                      {typeof currentData === 'object' && currentData?.title ? currentData.title : 'สรุปข้อมูล'}
                    </h5>
                    <div className="d-flex align-items-center gap-3">
                      <Button variant="outline-primary" size="sm" onClick={handleDownloadSummary}>
                        <i className="bi bi-save me-1"></i> บันทึก CSV
                      </Button>
                      <div className={`rounded-circle ${hasError ? 'bg-danger' : 'bg-success'}`} style={{ width: '12px', height: '12px' }} title="Status Indicator"></div>
                    </div>
                  </Card.Header>
                  <Card.Body>
                    <Row className="border-bottom py-2">
                      <Col xs={4} className="fw-semibold text-muted">สถานะ</Col>
                      <Col xs={8} className="text-end fw-medium">
                        {typeof currentData === 'object' && currentData?.status ? (
                           <Badge bg={currentData.status.toLowerCase() === 'live' ? 'success' : 'secondary'}>{currentData.status}</Badge>
                        ) : '-'}
                      </Col>
                    </Row>
                    <Row className="border-bottom py-2">
                      <Col xs={4} className="fw-semibold text-muted">ยอดคนดู</Col>
                      <Col xs={8} className="text-end fw-medium">
                        {typeof currentData === 'object' && currentData?.viewers !== undefined ? currentData.viewers.toLocaleString() : '-'}
                      </Col>
                    </Row>
                    <Row className="py-2">
                      <Col xs={4} className="fw-semibold text-muted">ลิงก์</Col>
                      <Col xs={8} className="text-end fw-medium">
                        {typeof currentData === 'object' && currentData?.url ? (
                          <a href={currentData.url} target="_blank" rel="noreferrer" className="text-decoration-none">
                            ดูไลฟ์สด <i className="bi bi-box-arrow-up-right small"></i>
                          </a>
                        ) : '-'}
                      </Col>
                    </Row>
                  </Card.Body>
                </Card>
              </Col>

              <Col md={12}>
                <Card className="shadow-sm border-0 h-100">
                  <Card.Header className="bg-white border-bottom d-flex justify-content-between align-items-center py-3">
                    <h5 className="mb-0 fw-bold">
                      <i className="bi bi-chat-dots me-2"></i> ข้อความแชท
                    </h5>
                    <Button variant="outline-primary" size="sm" onClick={handleDownloadChat}>
                      <i className="bi bi-save me-1"></i> บันทึก CSV
                    </Button>
                  </Card.Header>
                  <Card.Body className="p-0">
                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      <Table hover responsive className="mb-0 align-middle">
                        <thead className="table-light sticky-top">
                          <tr>
                            <th className="ps-4" style={{ width: '15%' }}>ลำดับ</th>
                            <th style={{ width: '30%' }}>ผู้ส่ง</th>
                            <th>ข้อความ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {typeof currentData === 'object' && currentData?.chat_messages?.length > 0 ? (
                            currentData.chat_messages.map((chat, index) => (
                              <tr key={chat.id || index}>
                                <td className="ps-4 text-muted small">{chat.id || index + 1}</td>
                                <td className="fw-medium">{chat.sender || 'ไม่ทราบชื่อ'}</td>
                                <td>{chat.message || ''}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="3" className="text-center py-5 text-muted">ไม่มีข้อความ</td>
                            </tr>
                          )}
                        </tbody>
                      </Table>
                    </div>
                  </Card.Body>
                </Card>
              </Col>

              <Col md={12}>
                <Card className="shadow-sm border-0">
                  <Card.Header className="bg-white border-bottom d-flex justify-content-between align-items-center py-3">
                    <h5 className="mb-0 fw-bold">
                      <i className="bi bi-filetype-json me-2"></i> ข้อมูลดิบ (Raw JSON)
                    </h5>
                    <Button variant="outline-primary" size="sm" onClick={handleDownloadJson}>
                      <i className="bi bi-save me-1"></i> บันทึก JSON
                    </Button>
                  </Card.Header>
                  <Card.Body className="bg-light" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    <pre className="mb-0" style={{ fontSize: '0.85rem' }}><code>
                      {currentData ? (typeof currentData === 'object' ? JSON.stringify(currentData, null, 2) : currentData) : 'รอรับข้อมูล...'}
                    </code></pre>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </div>
        )}
      </main>

      {/* API Guide Modal */}
      <Modal show={apiGuideModal} onHide={() => setApiGuideModal(false)} centered>
        <Modal.Header closeButton className="border-0 pb-0">
          <Modal.Title className="fw-bold">
            <i className="bi bi-key text-primary me-2"></i> วิธีขอรับ Tik Tools API Key
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="pt-2">
          <ol className="mb-0 ps-3">
            <li className="mb-2">ไปที่เว็บไซต์ <a href="https://tik.tools/" target="_blank" rel="noreferrer" className="fw-bold text-decoration-none">https://tik.tools/</a></li>
            <li className="mb-2">สมัครสมาชิก หรือ Login เข้าสู่ระบบ</li>
            <li>ไปที่เมนูเพื่อสร้าง/คัดลอก API Key ของคุณ</li>
          </ol>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0">
          <Button variant="primary" onClick={() => setApiGuideModal(false)}>
            ตกลง (OK)
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Alert Modal */}
      <Modal show={alertModal.show} onHide={() => setAlertModal({ show: false, title: '', message: '' })} centered>
        <Modal.Header closeButton className="border-0 pb-0">
          <Modal.Title className="fw-bold">
             {alertModal.title === 'สำเร็จ' ? <i className="bi bi-check-circle-fill text-success me-2"></i> : <i className="bi bi-exclamation-triangle-fill text-warning me-2"></i>}
             {alertModal.title}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="pt-2">
          <p className="mb-0">{alertModal.message}</p>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0">
          <Button variant="primary" onClick={() => setAlertModal({ show: false, title: '', message: '' })}>
            ตกลง (OK)
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}

export default App;
