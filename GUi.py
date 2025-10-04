import wx, cloudscraper, time, gc, winsound, math
from bs4 import BeautifulSoup
from datetime import datetime

# API URLs
LOGIN_URL = "https://www.yourrurl.me/api/checkuserlogin.php"
SPENTHISTORY_URL = "https://www.yourrurl.me/api/spenthistory.php"
INDEX_URL = "https://www.yourrurl.me/index.php"

# Headers
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "X-Requested-With": "XMLHttpRequest"
}

USERNAME = ""
PASSWORD = ""

scraper = cloudscraper.create_scraper()

# === SpendHistory Çekme ===
def fetch_all_unique_names_sorted():
    ts = int(time.time() * 1000)
    r = scraper.get(SPENTHISTORY_URL, headers=HEADERS, params={"draw": "1", "start": "0", "length": "1", "_": str(ts)})
    data = r.json()
    total = data.get("recordsTotal", 0)

    length = 100
    pages = math.ceil(total / length)
    all_rows = []

    for p in range(pages):
        start = p * length
        params = {
            "draw": str(p + 2),
            "start": str(start),
            "length": str(length),
            "order[0][column]": "3",
            "order[0][dir]": "asc",
            "_": str(int(time.time() * 1000))
        }
        r = scraper.get(SPENTHISTORY_URL, headers=HEADERS, params=params)
        d = r.json()
        all_rows.extend(d.get("data", []))

    def parse_date(row):
        try:
            return datetime.strptime(row[3], "%d/%m/%Y %H:%M:%S")
        except:
            return datetime.min

    all_rows.sort(key=parse_date, reverse=True)

    seen = set()
    performers = []
    for row in all_rows:
        if len(row) >= 4:
            name = row[0]
            pid = row[-1]
            date_str = row[3]
            if name not in seen:
                performers.append({
                    "name": name,
                    "id": pid,
                    "label": f"{name} ({pid}) [{date_str}]",
                    "short_label": f"{name} ({pid})"
                })
                seen.add(name)

    return performers


# === Login Dialog ===
class LoginDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="SDME Yayıncı Takip Aracı 1.2", size=(350, 200))
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)

        v.Add(wx.StaticText(p, label="Kullanıcı Adı:"), 0, wx.ALL, 5)
        self.username = wx.TextCtrl(p)
        v.Add(self.username, 0, wx.EXPAND | wx.ALL, 5)

        v.Add(wx.StaticText(p, label="Şifre:"), 0, wx.ALL, 5)
        self.password = wx.TextCtrl(p, style=wx.TE_PASSWORD)
        v.Add(self.password, 0, wx.EXPAND | wx.ALL, 5)

        h = wx.BoxSizer(wx.HORIZONTAL)
        h.Add(wx.Button(p, wx.ID_OK, "Giriş"), 0, wx.ALL, 5)
        h.Add(wx.Button(p, wx.ID_CANCEL, "İptal"), 0, wx.ALL, 5)
        v.Add(h, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        p.SetSizer(v)
        self.Centre()

    def get_credentials(self):
        return self.username.GetValue(), self.password.GetValue()


# === Selector Dialog ===
class SelectorDialog(wx.Dialog):
    def __init__(self, parent, title, data_list):
        super().__init__(parent, title=title, size=(500, 600))
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(p, label=f"Seçmek istediğiniz kişileri işaretleyin ({len(data_list)} kişi):")
        v.Add(info, 0, wx.ALL, 10)

        choices = [item["label"] for item in data_list]
        self.checklist = wx.CheckListBox(p, choices=choices)
        v.Add(self.checklist, 1, wx.EXPAND | wx.ALL, 10)

        btn_h = wx.BoxSizer(wx.HORIZONTAL)
        select_all = wx.Button(p, label="Tümünü Seç")
        select_all.Bind(wx.EVT_BUTTON, self.select_all)
        btn_h.Add(select_all, 0, wx.ALL, 5)

        clear_all = wx.Button(p, label="Tümünü Kaldır")
        clear_all.Bind(wx.EVT_BUTTON, self.clear_all)
        btn_h.Add(clear_all, 0, wx.ALL, 5)
        v.Add(btn_h, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(p, wx.ID_OK, "Takip Et")
        cancel_btn = wx.Button(p, wx.ID_CANCEL, "İptal")
        ok_cancel.Add(ok_btn, 0, wx.ALL, 5)
        ok_cancel.Add(cancel_btn, 0, wx.ALL, 5)
        v.Add(ok_cancel, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        p.SetSizer(v)
        self.data_list = data_list

    def select_all(self, event):
        for i in range(self.checklist.GetCount()):
            self.checklist.Check(i, True)

    def clear_all(self, event):
        for i in range(self.checklist.GetCount()):
            self.checklist.Check(i, False)

    def get_selected_items(self):
        return [self.data_list[i] for i in self.checklist.GetCheckedItems()]


# === Ana Frame ===
class TrackerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="SDME Yayıncı Takip Aracı 1.2",
                         size=(820, 450),
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.MAXIMIZE_BOX | wx.RESIZE_BORDER))
        self.Center()
        self.logged_in = False
        self.selected_items = []
        self.tracking_active = False

        dlg = LoginDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            global USERNAME, PASSWORD
            USERNAME, PASSWORD = dlg.get_credentials()
            dlg.Destroy()
        else:
            dlg.Destroy()
            self.Close()
            return

        self.init_ui()

        if self.do_login():
            self.status.SetLabel("Giriş başarılı, seçim yapabilirsiniz.")
        else:
            wx.MessageBox("Giriş başarısız!", "Hata", wx.OK | wx.ICON_ERROR)
            self.Close()

    # ---------------- UI ----------------
    def init_ui(self):
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        self.status = wx.StaticText(p, label="Giriş yapılıyor...")
        v.Add(self.status, 0, wx.ALL, 5)

        h = wx.BoxSizer(wx.HORIZONTAL)
        ob = wx.StaticBox(p, label="GENEL ODADA")
        ob.SetForegroundColour(wx.Colour(0, 128, 0))
        self.online_list = wx.ListBox(p)
        os = wx.StaticBoxSizer(ob, wx.VERTICAL)
        os.Add(self.online_list, 1, wx.EXPAND | wx.ALL, 5)

        pb = wx.StaticBox(p, label="ÖZEL ODADA")
        pb.SetForegroundColour(wx.Colour(200, 0, 0))
        self.private_list = wx.ListBox(p)
        ps = wx.StaticBoxSizer(pb, wx.VERTICAL)
        ps.Add(self.private_list, 1, wx.EXPAND | wx.ALL, 5)

        ofb = wx.StaticBox(p, label="SİSTEMDE YOK")
        ofb.SetForegroundColour(wx.Colour(128, 128, 128))
        self.offline_list = wx.ListBox(p)
        ofs = wx.StaticBoxSizer(ofb, wx.VERTICAL)
        ofs.Add(self.offline_list, 1, wx.EXPAND | wx.ALL, 5)

        h.Add(os, 1, wx.EXPAND | wx.ALL, 5)
        h.Add(ps, 1, wx.EXPAND | wx.ALL, 5)
        h.Add(ofs, 1, wx.EXPAND | wx.ALL, 5)
        v.Add(h, 1, wx.EXPAND | wx.ALL, 10)

        btn_h = wx.BoxSizer(wx.HORIZONTAL)
        site_select_btn = wx.Button(p, label="Aktif Yayıncı Seç")
        site_select_btn.Bind(wx.EVT_BUTTON, self.open_site_selector)
        btn_h.Add(site_select_btn, 0, wx.ALL, 5)

        giftlist_btn = wx.Button(p, label="Sohbet Listem")
        giftlist_btn.Bind(wx.EVT_BUTTON, self.show_giftlist)
        btn_h.Add(giftlist_btn, 0, wx.ALL, 5)

        clear_all_btn = wx.Button(p, label="Tümünü Temizle")
        clear_all_btn.Bind(wx.EVT_BUTTON, self.clear_all_tracking)
        btn_h.Add(clear_all_btn, 0, wx.ALL, 5)

        v.Add(btn_h, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        p.SetSizer(v)

    # ---------------- LOGIN ----------------
    def do_login(self):
        try:
            data = {"username": USERNAME, "password": PASSWORD}
            response = scraper.post(LOGIN_URL, headers=HEADERS, data=data, timeout=10)
            if "success" in response.text.lower():
                scraper.get(INDEX_URL, headers=HEADERS)
                self.logged_in = True
                return True
            else:
                return False
        except Exception as e:
            self.status.SetLabel(f"Giriş hatası: {str(e)}")
            return False

    # ---------------- FONKSİYONLAR ----------------
    def load_performers_from_site(self):
        performers = []
        try:
            soup = BeautifulSoup(scraper.get(INDEX_URL).content, "html.parser")
            seen = set()
            for tag in soup.select("a[href*='performerchat.php?id='], a[href*='profile.php?id=']"):
                name_tag = tag.select_one("strong")
                if name_tag and "id=" in tag.get("href", ""):
                    pid = tag.get("href").split("id=")[1]
                    name = name_tag.text.strip()
                    if pid not in seen:
                        seen.add(pid)
                        performers.append({
                            "name": name,
                            "id": pid,
                            "label": f"{name} ({pid})",
                            "short_label": f"{name} ({pid})"
                        })
        except:
            pass
        return performers

    def open_site_selector(self, event):
        performers = self.load_performers_from_site()
        if not performers:
            wx.MessageBox("Siteden yayıncı listesi alınamadı!", "Hata", wx.OK | wx.ICON_ERROR)
            return
        dlg = SelectorDialog(self, "Aktif Yayıncı Seç", performers)
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.get_selected_items()
            for item in selected:
                if not any(existing["id"] == item["id"] for existing in self.selected_items):
                    self.selected_items.append({
                        "name": item["name"],
                        "id": item["id"],
                        "label": item["short_label"]
                    })
            if self.selected_items:
                self.status.SetLabel(f"Siteden {len(selected)} kişi eklendi, toplam {len(self.selected_items)} takipte")
                self.start_tracking()
        dlg.Destroy()

    def show_giftlist(self, event):
        performers = fetch_all_unique_names_sorted()
        if not performers:
            wx.MessageBox("Henüz hiç sohbet etmediniz!", "Bilgi", wx.OK | wx.ICON_INFORMATION)
            return

        dlg = SelectorDialog(self, "Sohbet Listem", performers)
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.get_selected_items()
            for item in selected:
                if not any(existing["id"] == item["id"] for existing in self.selected_items):
                    self.selected_items.append({
                        "name": item["name"],
                        "id": item["id"],
                        "label": item["short_label"]
                    })
            if self.selected_items:
                self.status.SetLabel(f"Sohbet Listesinden {len(selected)} kişi eklendi, toplam {len(self.selected_items)} takipte")
                self.start_tracking()
        dlg.Destroy()

    # ---------------- TAKİP ----------------
    def start_tracking(self):
        self.tracking_active = True
        self.run_check_once()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(5000)

    def on_timer(self, event):
        if self.tracking_active and self.logged_in and self.selected_items:
            self.check_status_once()

            # 🔹 Her kontrol turunda genel oda doluysa ses çal
            online_count = self.online_list.GetCount()

            # 5 saniyede bir çalsın ama sadece genel oda doluysa
            if online_count > 0:
                try:
                    sound_path = r"C:\Windows\Media\Windows Hardware Fail.wav"
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception as e:
                    print(f"[!] Ses çalınamadı: {e}")


    def clear_all_tracking(self, event):
        self.tracking_active = False
        if hasattr(self, "timer"):
            self.timer.Stop()
        self.selected_items = []
        self.online_list.Clear()
        self.private_list.Clear()
        self.offline_list.Clear()
        self.status.SetLabel("Tüm takipler temizlendi.")
        self.online_list.GetContainingSizer().GetStaticBox().SetLabel("GENEL ODADA (0)")
        self.private_list.GetContainingSizer().GetStaticBox().SetLabel("ÖZEL ODADA (0)")
        self.offline_list.GetContainingSizer().GetStaticBox().SetLabel("SİSTEMDE YOK (0)")
        self.Layout()

    def run_check_once(self):
        self.check_status_once()

    def check_status_once(self):
        try:
            response = scraper.get(INDEX_URL, headers=HEADERS, timeout=10)
            html = response.text
            online, private, offline = [], [], []

            for item in self.selected_items:
                pid = item["id"]
                label = item["label"]

                is_public = f"performerchat.php?id={pid}" in html
                is_private = f"profile.php?id={pid}" in html

                if is_public:
                    online.append(label)
                elif is_private:
                    private.append(label)
                else:
                    offline.append(label)

            wx.CallAfter(self.online_list.Clear)
            wx.CallAfter(self.online_list.AppendItems, online)
            wx.CallAfter(self.private_list.Clear)
            wx.CallAfter(self.private_list.AppendItems, private)
            wx.CallAfter(self.offline_list.Clear)
            wx.CallAfter(self.offline_list.AppendItems, offline)

            wx.CallAfter(self.online_list.GetContainingSizer().GetStaticBox().SetLabel,
                         f"GENEL ODADA ({len(online)})")
            wx.CallAfter(self.private_list.GetContainingSizer().GetStaticBox().SetLabel,
                         f"ÖZEL ODADA ({len(private)})")
            wx.CallAfter(self.offline_list.GetContainingSizer().GetStaticBox().SetLabel,
                         f"SİSTEMDE YOK ({len(offline)})")
            wx.CallAfter(self.Layout)
            
            # 🔹 5 kontrolde bir bellek temizle
            self.gc_counter = getattr(self, "gc_counter", 0) + 1
            if self.gc_counter >= 5:
                gc.collect()
                self.gc_counter = 0

        except Exception as e:
            wx.CallAfter(self.status.SetLabel, f"Kontrol hatası: {str(e)}")


# === Main ===
if __name__ == "__main__":
    app = wx.App(False)
    TrackerFrame().Show()
    app.MainLoop()

