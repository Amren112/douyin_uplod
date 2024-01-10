import asyncio
import hashlib
import logging
import random
import re
import time

import cv2
import requests
from PIL import Image
from moviepy.editor import *
from playwright.async_api import Playwright, async_playwright

import config
from config import conigs
from logs import config_log


def get_file_md5(file_path):
    """
    取文件md5
    :param file_path:
    :return:
    """
    with open(file_path, 'rb') as file:
        content = file.read()
    md5_obj = hashlib.md5()
    md5_obj.update(content)
    return md5_obj.hexdigest()


def merge_images_video(image_folder, output_file, video_path):
    """
    把图片合并成视频并添加背景音乐
    :param image_folder: 图片文件夹路径
    :param output_file: 输出视频文件路径
    :param video_path: 待提取背景音乐的视频文件路径
    :return:
    """
    # 获取文件夹内所有图片的列表
    image_list = os.listdir(image_folder)
    # 获取图片总数量
    index = len(image_list)

    # 获取第一张图片的大小作为视频分辨率
    first_img = Image.open(image_folder + image_list[0])

    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4格式
        videowrite = cv2.VideoWriter(output_file, fourcc, 30, first_img.size)
        img_array = []
        for filename in [r'./frames/{0}.jpg'.format(i) for i in range(19, index + 19)]:
            img = cv2.imread(filename)
            if img is None:
                print("is error!")
                continue
            img_array.append(img)
        # 合成视频
        for i in range(1, len(img_array)):
            img_array[i] = cv2.resize(img_array[i], first_img.size)
            videowrite.write(img_array[i])
            print('第{}张图片合成成功'.format(i))
        # 关闭视频流
        videowrite.release()

        print('开始添加背景音乐！')
        # 初始化视频文件对象
        clip = VideoFileClip(video_path)
        # 从某个视频中提取一段背景音乐
        audio = AudioFileClip(video_path).subclip(0, 83)
        # 将背景音乐写入.mp3文件
        output_dir = "music/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            config.delete_all_files(output_dir)
        audio.write_audiofile(output_dir + '/background.mp3')
        # 向合成好的视频中添加背景音乐，需要同步秒数
        clip = clip.set_audio(audio)
        # 保存视频
        clip.write_videofile(output_file)
        print('背景音乐添加完成！')

    except Exception as e:
        print("发生错误：", str(e))
        logging.info(str(e))


def set_video_frame(video_path):
    """
    抽取视频帧，返回fps用于后面合成
    :param video_path: 视频文件路径
    :return:
    """
    # 打开视频文件
    video = cv2.VideoCapture(video_path)

    # 获取视频的帧数、每秒帧数等信息
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)

    # 设置要提取的帧数范围
    start_frame = 19  # 起始帧，剔除前面20帧和结尾10帧
    end_frame = frame_count - 11  # 结束帧

    # 创建保存抽取帧的目录
    output_dir = 'frames/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        config.delete_all_files(output_dir)

    # 定位到指定的起始帧
    video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # 按照指定的间隔提取并保存帧图像
    for i in range(start_frame, end_frame + 1):
        ret, frame = video.read()
        if not ret:
            break
        output_file = f'{output_dir}{i}.jpg'
        cv2.imwrite(output_file, frame)

        print(f"已处理 {i + 1}/{end_frame} 帧")

    print("所有帧都已成功抽取！")
    # 关闭视频流
    video.release()
    return fps


class douyin(object):
    def __init__(self):
        config_log()
        self.title = ""
        self.ids = ""
        self.video_path = ""
        self.path = os.path.abspath('')
        self.cid = "d9ba8ae07d955b83c3b04280f3dc5a4a"
        self.ua = {
            "web": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
                   "Safari/537.36",
            "app": "com.ss.android.ugc.aweme/110101 (Linux; U; Android 5.1.1; zh_CN; MI 9; Build/NMF26X; "
                   "Cronet/TTNetVersion:b4d74d15 2020-04-23 QuicVersion:0144d358 2020-03-24)"
        }

    def get_appkey(self):
        data = self.cid + '5c6b8r9a'
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def set_sign(self):
        ts = str(time.time()).split('.')[0]
        string = '1005' + self.cid + ts + self.get_appkey()
        sign = hashlib.md5(string.encode('utf8')).hexdigest()
        return sign

    def get_web_xbogus(self, url, ua):
        """
        获取web xbogus
        :param url:
        :param ua:
        :return:
        """
        sign_url = 'http://api2.52jan.com/dyapi/web/xbogus'
        ts = str(time.time()).split('.')[0]
        header = {
            'cid': self.cid,
            'timestamp': ts,
            'user-agent': 'okhttp/3.10.0.12'
        }
        sign = self.set_sign()
        params = {
            'url': url,
            'ua': ua,
            'sign': sign
        }
        resp = requests.post(sign_url, data=params, headers=header).json()
        return resp

    def get_douyin_music(self):
        """
        获取抖音Top50音乐榜单
        :return:
        """
        url = f"https://api3-normal-c-hl.amemv.com/aweme/v1/chart/music/list/?request_tag_from=rn&chart_id=6853972723954146568" \
              f"&count=100&cursor=0&os_api=22&device_type=MI 9" \
              f"&ssmix=a&manifest_version_code=110101&dpi=240&uuid=262324373952550&app_name=aweme&version_name=11.1.0&ts={round(time.time())}" \
              f"&cpu_support64=false&app_type=normal&ac=wifi&host_abi=armeabi-v7a&update_version_code" \
              f"=11109900&channel=douyinw&_rticket={round(time.time() * 1000)}&device_platform=android&iid=157935741181076" \
              f"&version_code=110100&cdid=02a0dd0b-7ed3-4bb4-9238-21b38ee513b2&openudid=af450515be7790d1&device_id=3166182763934663" \
              f"&resolution=720*1280&os_version=5.1.1&language=zh&device_brand=Xiaomi&aid=1128&mcc_mnc=46007"

        try:
            res = requests.get(url, headers={"User-Agent": self.ua["app"]}).json()
            x = random.randint(0, len(res["music_list"]) - 1)
            music_list = res["music_list"][x]
            self.title = f"-来自：榜单的第{(x + 1)}个音乐《{music_list['music_info']['title']}》"
            self.ids = music_list["music_info"]["id_str"]
            return self.get_douyin_music_video()
        except Exception:
            logging.info("获取抖音Top50音乐榜单失败")
            return 2

    def get_douyin_music_video(self, music_id=None):
        """
        根据音乐id获取音乐视频列表
        :param music_id:
        :return:
        """

        if music_id is None:
            music_id = self.ids if self.ids else "7315704709279550259"

        url = f"https://www.douyin.com/aweme/v1/web/music/aweme/?device_platform=webapp&aid=6383&channel" \
              f"=channel_pc_web&count=12&cursor=0&music_id={music_id}&pc_client_type=1&version_code=170400" \
              f"&version_name=17.4.0&cookie_enabled=true&screen_width=1536&screen_height=864&browser_language=zh-CN" \
              f"&browser_platform=Win32&browser_name=Chrome&browser_version=120.0.0.0&browser_online=true&engine_name" \
              f"=Blink&engine_version=120.0.0.0&os_name=Windows&os_version=10&cpu_core_num=8&device_memory=8&platform" \
              f"=PC&downlink=10&effective_type=4g&round_trip_time=50"

        headers = {
            "Host": "www.douyin.com",
            "Connection": "keep-alive",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "Accept": "application/json, text/plain, */*",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": self.ua["web"],
            "sec-ch-ua-platform": "\"Windows\"",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.douyin.com/music/" + music_id,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": "xgplayer_user_id=459752888030; pwa2=%223%7C0%7C3%7C1%22; passport_assist_user=CkGyBn6eg6zjcpMET_gHfmAf_TtK5p4ATeyNqMCnJiSyp3G-MdP53rUjgWZhWERMfhBYJ7tlXgWZ7jucLWGtE4PtVxpICjxXsqVzyUTBpdMnLIDRi5dvpas0rR82r0qc4cLRrFyu15Wh0g38ku3L0uRYSxbGIvAHPxZ9ncBkSkBEyjYQp-21DRiJr9ZUIgEDg_DXCw%3D%3D; sso_uid_tt=9dffe4dba6a6c536890ab0676b9b7ba2; sso_uid_tt_ss=9dffe4dba6a6c536890ab0676b9b7ba2; toutiao_sso_user=1764d3273a42231c9c6677ce8008f93b; toutiao_sso_user_ss=1764d3273a42231c9c6677ce8008f93b; LOGIN_STATUS=1; store-region=cn-jx; store-region-src=uid; __live_version__=%221.1.1.1853%22; my_rd=2; ttwid=1%7Cq4SP8Zou26ZvkihgcgQ1GXXpu9ztUlyp2CzWTDyx84o%7C1699872368%7C4fc1d73151991074d38b6d45a000d594a38a40584ae6ddabad40c850ed03bdb3; odin_tt=9494fb81f9c287d8518169efd75a7c74c649c19906587635766fabb5c18079ab775ffbfc9e0a77e0bfde886739516c1d; sid_ucp_sso_v1=1.0.0-KGE4M2Q5YzlhYTEwMGMyNzE4MzRiYmIyN2Q2MTk5MTgzMjAyOTI5NGUKHwj4ueCXiPTvAhCe-deqBhjvMSAMMK3goPgFOAZA9AcaAmxmIiAxNzY0ZDMyNzNhNDIyMzFjOWM2Njc3Y2U4MDA4ZjkzYg; ssid_ucp_sso_v1=1.0.0-KGE4M2Q5YzlhYTEwMGMyNzE4MzRiYmIyN2Q2MTk5MTgzMjAyOTI5NGUKHwj4ueCXiPTvAhCe-deqBhjvMSAMMK3goPgFOAZA9AcaAmxmIiAxNzY0ZDMyNzNhNDIyMzFjOWM2Njc3Y2U4MDA4ZjkzYg; sid_guard=1764d3273a42231c9c6677ce8008f93b%7C1700134046%7C5184001%7CMon%2C+15-Jan-2024+11%3A27%3A27+GMT; uid_tt=9dffe4dba6a6c536890ab0676b9b7ba2; uid_tt_ss=9dffe4dba6a6c536890ab0676b9b7ba2; sid_tt=1764d3273a42231c9c6677ce8008f93b; sessionid=1764d3273a42231c9c6677ce8008f93b; sessionid_ss=1764d3273a42231c9c6677ce8008f93b; bd_ticket_guard_client_web_domain=2; s_v_web_id=verify_lqsxttbt_gXy5ddyz_BwZv_4eEB_8hHF_vEwLeEmJ2fYo; dy_swidth=1536; dy_sheight=864; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; passport_csrf_token=0cb1deac0e53174e3ee1575c4e2388cc; passport_csrf_token_default=0cb1deac0e53174e3ee1575c4e2388cc; douyin.com; device_web_cpu_core=8; device_web_memory_size=8; architecture=amd64; csrf_session_id=a30df517c569ec0463ff6e2ea6311c3e; strategyABtestKey=%221704788190.67%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; __ac_signature=_02B4Z6wo00f01pZ-fkAAAIDBq9dk3Pp4of6WXnrAAMAOslG9amPQoCeDQ8cUza7yU.Rb.ZF5bNch-zFUhr-7UFOUP0fS1nDimzwGJQf4p8.Unah97KTARZJRGWe3T0PlKgEKFSnSzPTPKBqq76; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCRUZIQk5OSndxUU5JSkNTWSsyNWtOWC9SVVpDc0NPZ3VHdTBLMG5vVXBpeWJpSkEzU3FTakJHZmd0dGRxM2FZRFZrbytkeWtHL2pLb09FK2pzMjdQK3M9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoxfQ%3D%3D; xg_device_score=7.381583463336465; SEARCH_RESULT_LIST_TYPE=%22single%22; download_guide=%223%2F20240109%2F0%22; tt_scid=EwNKK20v8YCRpqoTO1b8O2OrzTMQcI5uVkhCBfb9..6TXEIIE9JFrXEX6MlO46wy7f34; msToken=ANr5MGvNqt9ZW7xysyENxKdEPLEeL2E8ovTD5w2kVIXUecLT2hGR2CtdoX9H8DcUmA5mbCnsjNCAfBf7rWjxfWItJABCWhbrQ-5DMeaH7RMmaDwKZNiWExJiDKSW; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; IsDouyinActive=true; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1536%2C%5C%22screen_height%5C%22%3A864%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A100%7D%22; home_can_add_dy_2_desktop=%221%22; msToken=X7t-JfesHFzGtWhp00GAQseZDZaEgJExCmd4f7wYdaxtCw3LPtU9hf4yFOrmfiez3No0Ip6tOsxtXNYS4jlIhA8pECK1A7V5pgkY-I914Zt_w11xjAmT-7ms0qI_"
        }
        xbogus = self.get_web_xbogus(url, self.ua["web"])
        url += '&X-Bogus=' + xbogus['xbogus']
        try:
            res = requests.get(url, headers=headers).json()
            video_list = {}
            if conigs.remove_enterprise:
                for i in range(len(res["aweme_list"])):
                    x = random.randint(0, len(res["aweme_list"]) - 1)
                    video_list = res['aweme_list'][x]
                    enterprise_verify_reason = video_list['author'].get("enterprise_verify_reason", "")
                    if not enterprise_verify_reason:
                        break
                    else:
                        print("已跳过企业号:" + enterprise_verify_reason)
            uri = video_list["video"]["play_addr_h264"]["url_list"][0]
            nickname = video_list['author']['nickname']
            # JSON.取通用属性 (“['aweme_list'][1].author['enterprise_verify_reason']”)
            # print(json.dumps(video_list))
            print("url:", uri)
            print("nickname:", nickname)

            # 获取自定义的视频标题
            self.title += f"@{nickname} 的作品"
            desc = random.choice(conigs.video_title_list) if conigs.title_random else ''.join(
                conigs.video_title_list)
            desc += ''.join(conigs.video_at) + self.title
            reb = requests.get(uri, headers={"User-Agent": self.ua["web"]}).content
            self.video_path = conigs.video_path + desc + ".mp4"
            with open(self.video_path, mode="wb") as f:
                f.write(reb)
                print("处理前md5：", get_file_md5(self.video_path))
                print("正在处理视频")
                clip = VideoFileClip(self.video_path)
                clip.subclip(6, 18)  # 剪切
                self.video_path = conigs.video_path + desc + "2.mp4"
                clip.write_videofile(self.video_path)  # 保存视频
                print("处理后md5：", get_file_md5(self.video_path))
                print("视频处理完毕")
                return 0
        except Exception as e:
            print("出现错误：", e)
            logging.info(e)
            return 1


class upload_douyin(douyin):
    def __init__(self, timeout: int, cookie_file: str):
        super(upload_douyin, self).__init__()
        """
        初始化
        :param timeout: 你要等待多久，单位秒
        :param cookie_file: cookie文件路径
        """
        self.timeout = timeout * 1000
        self.cookie_file = cookie_file

    async def upload(self, playwright: Playwright) -> None:

        browser = await playwright.chromium.launch(channel="chrome", headless=False)

        context = await browser.new_context(storage_state=self.cookie_file, user_agent=self.ua["web"])

        page = await context.new_page()
        await page.add_init_script("Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});")

        print("正在判断账号是否登录")
        try:
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await page.locator(".login").click(timeout=1500)
            print("未登录，正在跳出")
            logging.info("未登录，正在跳出")
            is_login = False
        except Exception as e:
            # print("出现此error，代表cookie正常反之异常\n", e)
            is_login = True
            print("账号已登录")
        if is_login:
            try:
                await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            except Exception as e:
                print("发布视频失败，cookie已失效，请登录后再试\n", e)
                logging.info("发布视频失败，cookie已失效，请登录后再试")

            video_desc_list = self.video_path.split("\\")
            video_desc = str(video_desc_list[len(video_desc_list) - 1])[:-4]

            video_desc_tag = []
            tag_rs = re.findall(r"(#.*?) ", video_desc)
            if len(tag_rs) > 0:
                video_desc_tag = video_desc.split(" ")
                print("该视频有话题")
            else:
                video_desc_tag.append(video_desc)
                print("该视频没有检测到话题")

            try:
                async with page.expect_file_chooser() as fc_info:
                    await page.locator(
                        "label:has-text(\"点击上传 或直接将视频文件拖入此区域为了更好的观看体验和平台安全，平台将对上传的视频预审。超过40秒的视频建议上传横版视频\")").click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.video_path, timeout=self.timeout)
            except Exception as e:
                print("发布视频失败，可能网页加载失败了\n", e)
                logging.info("发布视频失败，可能网页加载失败了")
            # await page.locator("label:has-text(\"点击上传 或直接将视频文件拖入此区域为了更好的观看体验和平台安全，平台将对上传的视频预审。超过40秒的视频建议上传横版视频\")").set_input_files("下载.mp4", timeout=self.timeout)
            try:
                await page.locator(".modal-button--38CAD").click()
            except Exception as e:
                print(e)
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page")
            # css视频标题选择器

            css_selector = ".zone-container"
            await page.locator(".ace-line > div").click()
            tag_index = 0
            at_index = 0
            # 处理末尾标题
            video_desc_end = len(video_desc_tag) - 1
            video_desc_tag[video_desc_end] = video_desc_tag[video_desc_end][:-2]
            for tag in video_desc_tag:
                await page.type(css_selector, tag)
                if "@" in tag:
                    at_index += 1
                    print("正在添加第%s个想@的人" % at_index)
                    time.sleep(1)
                    try:
                        await page.get_by_text(tag[1:], exact=True).click()
                    except Exception as e:
                        print(e)
                        print("@未能成功")
                    # await page.locator("div").filter(
                    #     has_text=re.compile(r"^" + tag[1:] + "$")).first.click()
                else:
                    tag_index += 1
                    await page.press(css_selector, "Space")
                    print("正在添加第%s个话题" % tag_index)
            print("视频标题输入完毕，等待发布")
            time.sleep(3)

            try:
                await page.locator('button.button--1SZwR:nth-child(1)').click()
            except Exception as e:
                print(e)
            # 获取点击按钮消息
            msg = await page.locator('//*[@class="semi-toast-content-text"]').all_text_contents()
            for msg_txt in msg:
                print("来自网页的实时消息：" + msg_txt)

            # 跳转成功页面
            try:
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage")
                print("账号发布视频成功")
                logging.info("账号发布视频成功")
            except Exception as e:
                is_while = False
                while True:
                    # 循环获取点击按钮消息
                    time.sleep(2)
                    try:
                        await page.locator('button.button--1SZwR:nth-child(1)').click()
                    except Exception as e:
                        print(e)
                        break
                    msg = await page.locator('//*[@class="semi-toast-content-text"]').all_text_contents()
                    for msg_txt in msg:
                        print("来自网页的实时消息：" + msg_txt)
                        if msg_txt == '发布成功':
                            is_while = True
                            logging.info("账号发布视频成功")
                            print("账号发布视频成功")
                        elif msg_txt == '上传成功':
                            try:
                                await page.locator('button.button--1SZwR:nth-child(1)').click()
                            except Exception as e:
                                print(e)
                                break
                            msg2 = await page.locator(
                                '//*[@class="semi-toast-content-text"]').all_text_contents()
                            for msg2_txt in msg2:
                                if msg2_txt == '发布成功':
                                    is_while = True
                                    logging.info("账号发布视频成功")
                                    print("账号发布视频成功")
                                elif msg2_txt.find("已封禁") != -1:
                                    is_while = True
                                    logging.info("账号视频发布功能已被封禁")
                                    print("账号视频发布功能已被封禁")
                        elif msg_txt.find("已封禁") != -1:
                            is_while = True
                            print("视频发布功能已被封禁")
                            logging.info("视频发布功能已被封禁")
                        else:
                            pass

                    if is_while:
                        break

        await context.close()
        await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            code = self.get_douyin_music()
            if code == 0:
                await self.upload(playwright)
            elif code == 1:
                print("视频下载失败")
            elif code == 2:
                print("音乐榜单获取失败")
            else:
                pass


if __name__ == '__main__':
    # path = r"E:\python\douyin\发布小程序\video\#庐陵老街老赖陈万洵 @庐陵老街陈万洵 -来自：榜单的第36个音乐《爱丫爱丫》@𝐹𝑜𝑟𝑒𝑣𝑒𝑟✨ 的作品.mp4"
    # fps = set_video_frame(path)
    # print("fps:", fps)
    # merge_images_video(os.path.abspath("") + "\\frames\\", r"E:\\python\\douyin\\发布小程序\\video\\output.mp4", path)
    app = upload_douyin(60, conigs.cookie_path)
    asyncio.run(app.main())
