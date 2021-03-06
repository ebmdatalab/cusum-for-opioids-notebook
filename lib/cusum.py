import numpy as np
import pandas as pd


def most_change_against_window(percentiles, window=12):
    """Use CUSUM algorithm to detect cumulative change from a reference
    mean averaged over the previous `window` months.

    Returns a list of dicts of `measure`, `from`, and `to`

    """
    improvements = []
    declines = []
    cusum = CUSUM(percentiles, window_size=window, sensitivity=5)
    cusum.work()

    last_alert = cusum.get_last_alert_info()
    if last_alert:
        if last_alert["from"] < last_alert["to"]:
            declines.append(last_alert)
        else:
            improvements.append(last_alert)
    improvements = sorted(improvements, key=lambda x: -abs(x["to"] - x["from"]))
    declines = sorted(declines, key=lambda x: -abs(x["to"] - x["from"]))
    return {"improvements": improvements, "declines": declines}


class CUSUM(object):
    """See Introduction to Statistical Quality Control, Montgomery DC, Wiley, 2009
    and our paper
    http://dl4a.org/uploads/pdf/581SPC.pdf
    """

    def __init__(self, data, window_size=12, sensitivity=5):
        data = np.array([np.nan if x is None else x for x in data])
        # Remove sufficient leading nulls to ensure we can start with
        # any value
        self.start_index = 0
        while pd.isnull(data[self.start_index : self.start_index + window_size]).all():
            if self.start_index > len(data):
                data = []
                break
            self.start_index += 1
        self.data = data
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.pos_cusums = []
        self.neg_cusums = []
        self.target_means = []
        self.alert_thresholds = []
        self.alert_indices = []
        self.pos_alerts = []
        self.neg_alerts = []

    def work(self):
        for i, datum in enumerate(self.data):
            if i <= self.start_index:
                window = self.data[i : self.window_size + i]
                self.new_target_mean(window)
                self.new_alert_threshold(window)
                self.compute_cusum(datum, reset=True)
            elif self.cusum_within_alert_threshold():
                # Note this will always be true for the first `window_size`
                # data points
                self.maintain_target_mean()
                self.maintain_alert_threshold()
                self.compute_cusum(datum)
            else:
                # Assemble a moving window of the last `window_size`
                # non-null values
                window = self.data[i - self.window_size : i]
                self.new_target_mean(window)
                if self.moving_in_same_direction(datum):  # this "peeks ahead"
                    self.maintain_alert_threshold()
                    self.compute_cusum(datum)
                else:
                    self.new_alert_threshold(window)  # uses window
                    self.compute_cusum(datum, reset=True)
            # Record alert
            self.record_alert(datum, i)
        return self.as_dict()

    def as_dict(self):
        return {
            "smax": self.pos_cusums,
            "smin": self.neg_cusums,
            "target_mean": self.target_means,
            "alert_threshold": self.alert_thresholds,
            "alert": self.alert_indices,
            "alert_percentile_pos": self.pos_alerts,
            "alert_percentile_neg": self.neg_alerts,
        }

    def get_last_alert_info(self):
        """If the current (most recent) month includes an alert, work out when
        that alert period started, and return numbers that approximate
        to the size of the change across that period.

        """
        if any(self.alert_indices) and self.alert_indices[-1] == len(self.data) - 1:
            end_index = start_index = self.alert_indices[-1]
            for x in list(reversed(self.alert_indices))[1:]:
                if x == start_index - 1:
                    start_index = x
                else:
                    break
            duration = (end_index - start_index) + 1
            return {
                "from": self.target_means[start_index - 1],
                "to": self.data[end_index],
                "period": duration,
            }
        else:
            return None

    def moving_in_same_direction(self, datum):
        # Peek ahead to see what the next CUSUM would be
        next_pos_cusum, next_neg_cusum = self.compute_cusum(datum, store=False)
        going_up = (
            next_pos_cusum > self.current_pos_cusum()
            and self.cusum_above_alert_threshold()
        )
        going_down = (
            next_neg_cusum < self.current_neg_cusum()
            and self.cusum_below_alert_threshold()
        )
        return going_up or going_down

    def __repr__(self):
        return """
        name:             {name}
        data:             {data}
        pos_cusums:       {pos_cusums}
        neg_cusums:       {neg_cusums}
        target_means:     {target_means}
        alert_thresholds: {alert_thresholds}"
        alert_incides:    {alert_indices}"
        """.format(
            **self.__dict__
        )

    def record_alert(self, datum, i):
        if self.cusum_above_alert_threshold():
            self.alert_indices.append(i)
            self.pos_alerts.append(datum)
            self.neg_alerts.append(None)
        elif self.cusum_below_alert_threshold():
            self.alert_indices.append(i)
            self.pos_alerts.append(None)
            self.neg_alerts.append(datum)
        else:
            self.pos_alerts.append(None)
            self.neg_alerts.append(None)

    def maintain_alert_threshold(self):
        self.alert_thresholds.append(self.alert_thresholds[-1])
        return self.alert_thresholds[-1]

    def maintain_target_mean(self):
        self.target_means.append(self.target_means[-1])
        return self.target_means[-1]

    def cusum_above_alert_threshold(self):
        return self.pos_cusums[-1] > self.alert_thresholds[-1]

    def cusum_below_alert_threshold(self):
        return self.neg_cusums[-1] < -self.alert_thresholds[-1]

    def cusum_within_alert_threshold(self):
        return not (
            self.cusum_above_alert_threshold() or self.cusum_below_alert_threshold()
        )

    def new_target_mean(self, window):
        self.target_means.append(np.nanmean(window))

    def new_alert_threshold(self, window):
        self.alert_thresholds.append(np.nanstd(window * self.sensitivity))

    def current_pos_cusum(self):
        return self.pos_cusums[-1]

    def current_neg_cusum(self):
        return self.neg_cusums[-1]

    def compute_cusum(self, datum, reset=False, store=True):
        alert_threshold = self.alert_thresholds[-1]
        delta = 0.5 * alert_threshold / self.sensitivity
        current_mean = self.target_means[-1]
        cusum_pos = datum - (current_mean + delta)
        cusum_neg = datum - (current_mean - delta)
        if not reset:
            cusum_pos += self.pos_cusums[-1]
            cusum_neg += self.neg_cusums[-1]
        cusum_pos = round(max(0, cusum_pos), 2)
        cusum_neg = round(min(0, cusum_neg), 2)
        if store:
            self.pos_cusums.append(cusum_pos)
            self.neg_cusums.append(cusum_neg)
        return cusum_pos, cusum_neg
