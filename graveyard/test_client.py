#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: BSD
#   https://raw.githubusercontent.com/splintered-reality/py_trees_ros_tutorials/devel/LICENSE
#
##############################################################################
# Imports
##############################################################################


import action_msgs.msg as action_msgs  # GoalStatus
import action_msgs.srv as action_srvs  # CancelGoal
import argparse
import py_trees_ros
import rclpy
import rclpy.action  # ActionClient
import sys
import test_msgs.action as test_actions
import unique_identifier_msgs.msg as unique_identifier_msgs
import uuid

##############################################################################
# Imports
##############################################################################


class ActionClient(object):
    """
    Generic action client that can be used to test the mock action servers.

    Args:
        node_name (:obj:`str`): name of the action server (e.g. move_base)
        action_name (:obj:`str`): name of the action server (e.g. move_base)
        action_type (:obj:`any`): type of the action server (e.g. move_base_msgs.msg.MoveBaseAction
        worker (:obj:`func`): callback to be executed inside the execute loop, no args
        goal_recieved_callback(:obj:`func`): callback to be executed immediately upon receiving a goal
        duration (:obj:`float`): forcibly override the dyn reconf time for a goal to complete (seconds)

    Use the ``dashboard`` to dynamically reconfigure the parameters.
    """
    def __init__(self,
                 node_name,
                 action_name,
                 action_type,
                 action_server_namespace,
                 cancel=False,
                 generate_feedback_message=None
                 ):
        self.action_type = action_type
        self.action_name = action_name
        self.action_server_namespace = action_server_namespace
        self.node_name = node_name
        if generate_feedback_message is None:
            self.generate_feedback_message = lambda msg: str(msg)
        else:
            self.generate_feedback_message = generate_feedback_message
        self.cancel = cancel

    def setup(self):
        self.node = rclpy.create_node(self.node_name)
        self.action_client = rclpy.action.ActionClient(
            node=self.node,
            action_type=self.action_type,
            action_name=self.action_name
        )
        self.node.get_logger().info(
            'waiting for server [{}]'.format(
                self.action_server_namespace
            )
        )
        result = self.action_client.wait_for_server(timeout_sec=2.0)
        if not result:
            message = "timed out waiting for the server [{}]".format(
                    self.action_server_namespace
                )
            self.node.get_logger().error(message)
            raise RuntimeError(message)

    def feedback_callback(self, msg):
        self.node.get_logger().info('feedback: {0}'.format(self.generate_feedback_message(msg)))

    def process_result(self, future):
        status = future.result().action_status
        if status == action_msgs.GoalStatus.STATUS_SUCCEEDED:
            self.node.get_logger().info('goal success!')
        else:
            self.node.get_logger().info('goal failed with status {0}'.format(status))

    def send_goal(self):
        goal_uuid = unique_identifier_msgs.UUID(
            uuid=list(uuid.uuid4().bytes)
        )
        self.node.get_logger().info('sending goal...')
        future = self.action_client.send_goal_async(
                self.action_type.Goal(),
                feedback_callback=self.feedback_callback,
                goal_uuid=goal_uuid)
        rclpy.spin_until_future_complete(self.node, future, self.executor)
        if future.result() is not None and future.result().accepted is True:
            self.node.get_logger().info("...goal accepted %s" % future.result())
        else:
            self.node.get_logger().info('...goal rejected [%r]' % (future.exception()))
        return future.result()

    def spin(self):
        self.executor = rclpy.executors.SingleThreadedExecutor()
        goal_handle = self.send_goal()
        if goal_handle is None:
            return
        result_future = goal_handle.get_result_async()
        self.executor.add_node(self.node)
        count = 0
        timeout_sec = 0.1
        while rclpy.ok() and not result_future.done():
            self.executor.spin_once(timeout_sec=timeout_sec)
            count += 1
            if count == int(1.0/timeout_sec):
                if self.cancel:
                    self.node.get_logger().info("sending a cancel request...")
                    cancel_future = goal_handle.cancel_goal_async()
        if self.cancel:
            if not cancel_future.done():
                self.node.get_logger().error("spin loop exited before receiving the cancel response")
            else:
                self.node.get_logger().info("cancelled [goal id: {}]".format(
                    cancel_future.result())  # .goals_canceling[0].goal_id) ... is empty?
                )
        if not result_future.done():
            self.node.get_logger().error("rclpy shut down before receiving the result")
        else:
            # Status: https://github.com/ros2/rcl_interfaces/blob/master/action_msgs/msg/GoalStatus.msg
            status_strings = {
                0: "STATUS_UNKNOWN",
                1: "STATUS_ACCEPTED",
                2: "STATUS_EXECUTING",
                3: "STATUS_CANCELING",
                4: "STATUS_SUCCEEDED",
                5: "STATUS_CANCELED",
                6: "STATUS_ABORTED"
            }
            self.node.get_logger().info("Result")
            self.node.get_logger().info("  status: {}".format(status_strings[result_future.result().action_status]))
            self.node.get_logger().info("  sequence: {}".format(str(result_future.result().sequence)))

    def shutdown(self):
        self.action_client.destroy()
        self.node.destroy_node()


##############################################################################
# Programs
##############################################################################


if __name__ == '__main__':
    rclpy.init()
    action_client = ActionClient(
        node_name="move_base_client",
        action_name="fibonacci",
        action_type=test_actions.Fibonacci,
        action_server_namespace="/move_base",
        cancel=False,
        generate_feedback_message=lambda msg: "{0}".format(msg.sequence),
    )
    try:
        action_client.setup()
        action_client.spin()
    except KeyboardInterrupt:
        pass
    action_client.shutdown()