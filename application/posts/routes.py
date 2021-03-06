from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from application.database import db
from application.models import Post, Tag
from application.posts.forms import PostForm
from application.posts.utils import save_thumbnail, save_image
import markdown2
import os
import secrets

posts = Blueprint("posts", __name__)

@posts.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
	form = PostForm()
	form.tags.choices = [(tag.name, tag.name) for tag in Tag.query.all()]
	if form.validate_on_submit():
		content = form.content.data
		attachments = request.files.getlist(form.attachments.name)

		if attachments and all(f for f in attachments):
			for attachment in attachments:
				_, file_extension = os.path.splitext(attachment.filename)
				if file_extension in [".jpg", ".jpeg", ".png", ".tiff"]:
					saved_image_path = save_image(attachment)
					content = content.replace(attachment.filename, saved_image_path)
				else:
					flash(f"{attachment.filename}: This file is not supported.", "warning")
		content = markdown2.markdown(content)

		thumbnail_filename = save_thumbnail(form.thumbnail.data) if form.thumbnail.data else "default.jpg"

		post = Post(title=form.title.data, content=content, author=current_user, draft=int(form.draft.data), thumbnail=thumbnail_filename)

		for tag_name in form.tags.data:
			tag = Tag.query.filter_by(name=tag_name).first()
			if tag_name == "Daily Digest": #clear all other tags with daily digest tag
				tag.posts = []
			tag.posts.append(post)

		db.session.add(post)
		db.session.commit()
		flash(f"Your post has been created! {form.draft.data} {type(form.draft.data)}", "success")
		return redirect(url_for("posts.post", post_id=post.id))

	return render_template("create_post.html", title="New Post", form=form)

@posts.route('/post/<int:post_id>', methods=["GET", "POST"])
def post(post_id):
	post = Post.query.get_or_404(post_id) #return post with this id; if it doesn't, return 404
	return render_template("post.html", title=post.title, post=post)

@posts.route('/post/<int:post_id>/update', methods=["GET", "POST"])
@login_required
def update_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.author != current_user:
		abort(403)

	form = PostForm()
	form.tags.choices = [(tag.name, tag.name) for tag in Tag.query.all()]
	if form.validate_on_submit():
		post.title = form.title.data

		content = form.content.data
		attachments = request.files.getlist(form.attachments.name)

		if attachments and all(f for f in attachments):
			for attachment in attachments:
				_, file_extension = os.path.splitext(attachment.filename)
				if file_extension in [".jpg", ".jpeg", ".png", ".tiff"]:
					saved_image_path = save_image(attachment)
					content = content.replace(attachment.filename, saved_image_path)
				else:
					flash(f"{attachment.filename}: This file is not supported.", "warning")
		post.content = markdown2.markdown(content)

		if form.thumbnail.data:
			post.thumbnail_filename = save_thumbnail(form.thumbnail.data)

		for tag in form.tags.data:
			tag = Tag.query.filter_by(name=tag).first()
			tag.posts.append(post)
		db.session.commit() #We're updating something that is already in the database, so no need for db.session.add()
		flash("Your post has been updated!", "success")
		return redirect(url_for("posts.post", post_id=post.id))
	elif request.method == "GET":
		form.title.data = post.title
		form.content.data = post.content
	return render_template("create_post.html", title="Update Post", form=form, legend="Update Post")

@posts.route('/post/<int:post_id>/delete', methods=["POST"]) #you can specfy the type of dynamic parameter - integers.
@login_required
def delete_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.author != current_user:
		abort(403)

	db.session.delete(post)
	db.session.commit()
	flash("Your post has been deleted!", "success")
	return redirect(url_for("main.home"))

@posts.route("/post/<string:tag_name>")
def tag_posts(tag_name):
	tag = Tag.query.filter_by(name=tag_name).first()
	if not tag:
		abort(404)
	posts = tag.posts.order_by(Post.date_posted.desc()).paginate(per_page=5) #use the backref to access all posts with the tag
	return render_template("tag_posts.html", tag=tag, title=tag.name, posts=posts)