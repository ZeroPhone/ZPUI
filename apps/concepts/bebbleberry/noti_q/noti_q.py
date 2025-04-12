from noti_q.notification import Notification


class NotificationQueue:
    def __init__(self):
        self.queue = []

    def add_notification(self, notification: Notification):
        self.queue.append(notification)

    def get_noticication(self):
        if len(self.queue) > 0:
            if self.queue[0].time <= 0:
                self.queue.pop()
            self.queue[0].time -= 1
            return self.queue[0].text
