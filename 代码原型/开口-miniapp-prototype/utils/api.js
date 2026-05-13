const BASE_URL = "http://127.0.0.1:8765";

function request({ url, method = "GET", data }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      timeout: 15000,
      success(response) {
        const payload = response.data || {};
        if (response.statusCode >= 200 && response.statusCode < 300 && payload.code === 0) {
          resolve(payload.data);
          return;
        }

        reject(new Error(payload.message || `request failed: ${response.statusCode}`));
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

module.exports = {
  BASE_URL,
  request
};
