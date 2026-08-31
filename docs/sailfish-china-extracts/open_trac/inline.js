
  (function () {
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    var raceCd = "";
    var rounds = "1";
    var stomp = "d3M6Ly9sb2NhbGhvc3Q6ODE4Ni93ZWJzb2NrZXQ/dG9rZW49c2FpbGZpc2g=";
    var replayFlag = false;
    var urlEnd = 'live2/'
    for (var i = 0; i < vars.length; i++) {
      var pair = vars[i].split("=");
      if (pair[0] == 'raceCd') {
        raceCd = pair[1];
      } else if (pair[0] == 'rounds') {
        rounds = pair[1];
      } else if (pair[0] == 'stomp') {
        stomp = pair[1];
      } else if (pair[0] == 'replayFlag') {
        if (pair[1] == 'true') {
          replayFlag = true;
          urlEnd = 'replay2/';
        }
      }
    }

    const getJSON = function (url, method) {
      const promise = new Promise(function (resolve, reject) {
        const handler = function () {
          if (this.readyState !== 4) {
            return;
          }
          if (this.status === 200) {
            resolve(this.response);
          } else {
            reject(new Error(this.statusText));
          }
        };
        const client = new XMLHttpRequest();
        client.open(method, url);
        client.onreadystatechange = handler;
        client.responseType = "json";
        client.setRequestHeader("Accept", 'application/json');
        client.send();

      });
      return promise;
    };

    let race = {}
    getJSON(window.g.BaseUrl + '/app-api/match/race/getRace?pageName=open_trac&raceCd=' + raceCd, "GET").then((json) => {
      // 已经结束的显示回放轨迹
      if (json.data.status == '99') {
        replayFlag = true;
        urlEnd = 'replay2/';
      }
      // 修改title
      document.title = json.data.raceName + ' ' + json.data.rounds + ' - SAILFISH SPORTS';
      race = json.data;
      // 获取基础URL部分（如：http://localhost:8080）
      var baseUrlWithPort = window.location.protocol + "//" + window.location.host;
      window.app = SF_TrajX({
        // 比赛系统
        raceCd: raceCd,
        url:  baseUrlWithPort + window.g.BaseUrl + '/app-api/match/race/' + urlEnd,
        method: 'getEncryption',
        lang: 'Ly93d3cuc2FpbGwuY24vY2RuL3NmLXRyYWovYXBwL3NhaWxpbmcvbGFuZ1gv',
        replay: replayFlag,
        club: false,
        layout: false,
        camera: true,
        toolShowAll: true,
        toolMeasuring: true,
        charts: false,
        teamList: true,
        route: baseUrlWithPort + window.g.BaseUrl + '/app-api/match/race/getRouteInfo?raceCd=' + raceCd,
      });
      isWeixin();
    }, function (error) {
      console.log('出错了', error);
    });

    //判断是否是微信浏览器
    const isWeixin = function () {
      //微信浏览器进行微信分享设定
      var url = window.location.href.split("#")[0];
      var matchLogo = race.matchLogo;
      if (matchLogo) {
        var dot = matchLogo.lastIndexOf(".")
        matchLogo = matchLogo.substring(0, dot) + "_logo300X300.jpg";
      } else {
        matchLogo = "https://www.saill.cn/file/image/logo/sf/sc" + race.matchCd + "_logo300X300.jpg";
      }
      var ua = navigator.userAgent.toLowerCase();
      if (ua.match(/MicroMessenger/i) == "micromessenger") {
        //通过ajax，在页面加载的时候获取微信分享接口signature，nonceStr，timestamp 和appId
        getJSON("https://www.saill.cn/cloudalbum-web/www/home/wechatConfig?url=" + encodeURIComponent(url), "GET").then((res) => {
          let data = res;
          wx.config({
            debug: false,
            appId: data.appId,
            timestamp: data.timestamp,
            nonceStr: data.nonceStr,
            signature: data.signature,
            jsApiList: [
              "onMenuShareTimeline",
              "onMenuShareAppMessage",
              "onMenuShareQQ",
              "onMenuShareWeibo",
              "onMenuShareQZone",
              'updateAppMessageShareData',
              'updateTimelineShareData'
            ],
          });
        });

        wx.ready(() => {
          var shareData = {
            title: race.matchName,
            desc: race.raceName + "-" + race.rounds,
            link: url,
            imgUrl: matchLogo,
            success: (e) => {
              console.log(e)
            },
            fail: function (e) {
              console.log(e)
            }
          };
          wx.onMenuShareTimeline(shareData);
          wx.onMenuShareAppMessage(shareData);
          wx.onMenuShareQQ(shareData);
          wx.onMenuShareWeibo(shareData);
          wx.onMenuShareQZone(shareData);
          wx.updateAppMessageShareData(shareData);
          wx.updateTimelineShareData(shareData);
        });

        wx.error(function (res) {
          console.error(res);
        });
      }
    }

  })();

