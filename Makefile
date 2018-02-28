IMAGE := $DOCKER_PROJECT/gridappsd:dev

#test:
#	true

image:
	docker build -t $(IMAGE) .

push-image:
    ifeq($TRAVIS_REPO_SLUG, 'craig8/GOSS-GRIDAPPS-D')
		docker push $(IMAGE)
	endif

.PHONY: image push-image 
# test
